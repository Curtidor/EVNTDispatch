import asyncio
import functools
import logging

from asyncio import AbstractEventLoop, Task, Future
from typing import Callable, Any, Set, List, Dict, Union, Coroutine, Tuple

from .event_listener import EventListener, Priority
from .event import Event


class EventDispatcher:
    """
    EventDispatcher handles event listeners, triggers events, and manages asynchronous execution of listeners.
    """
    UNLIMITED_RESPONDERS = -1

    def __init__(self, loop: asyncio.AbstractEventLoop = None, debug_mode: bool = False):
        """
        Initialize the EventDispatcher.

        :param debug_mode: Enable debug mode for logging.
        """
        self.debug_mode = debug_mode

        self._listeners: Dict[str, List['EventListener']] = {}
        self._sync_canceled_future_events: Dict[str, int] = {}
        self._running_async_tasks: Dict[str, List[Task]] = {}
        self._busy_listeners: Set[Coroutine] = set()

        # event loop
        self._event_queue_manager_task: Task = None # noqa
        self._event_loop = self._set_event_loop(loop)
        self._event_queue = asyncio.Queue()
        self._queue_empty_event = asyncio.Event()

        # tasks
        self._running_async_tasks: Dict[str, List[Task]] = {}
        self._time_until_final_task = 0

        # flags
        self._cancel_events = False
        self._is_queue_primed = False
        self._is_event_loop_running = False

    def start(self):
        """
        Start the event loop if not already running.
        """
        if not self._is_event_loop_running:
            self._event_queue_manager_task = self._event_loop.create_task(self._event_loop_runner())
            self._is_event_loop_running = True

    async def close(self, wait_for_scheduled_tasks: bool = True):
        """
        Close the event loop and wait for queued and scheduled events to be processed and ran.
        """
        if self._is_queue_primed:
            # wait for all events in the queue to be processed
            await self._queue_empty_event.wait()
        else:
            # if no events have been placed in the queue cancel the task, so we don't
            # indefinitely wait for an event
            self._event_queue_manager_task.cancel('canceling queue manager, due to no events to process')

        if wait_for_scheduled_tasks:
            # get the time left until the final task is complete
            final_task_complete_time = self._time_until_final_task - self._loop.time()
            # ensure the value is positive or zero(z)
            z_final_task_complete_time = final_task_complete_time if final_task_complete_time > 0 else 0
            await asyncio.sleep(z_final_task_complete_time)

        tasks = []
        for k, v in self._running_async_tasks.items():
            for task in v:
                if task.cancelled():
                    continue
                tasks.append(task)

        for task in asyncio.all_tasks(loop=self._event_loop):
            if task.get_coro().__name__ == "_async_trigger":
                tasks.append(task)
        # wait for all the running events to finish
        await asyncio.gather(*tasks)
        self._is_event_loop_running = False

    def add_listener(self, event_name: str, listener: Callable, priority: Priority = Priority.NORMAL, allow_busy_trigger: bool = True) -> None:
        """
        Add a listener to the event.

        :param allow_busy_trigger: allow the listener to be trigger even if it's still running
        :param event_name: Name of the event.
        :param listener: Callable object representing the listener function.
        :param priority: Priority of the listener.
        """
        if callable(listener):
            self._register_event_listener(event_name, listener, priority, allow_busy_trigger)
            self._sort_listeners(event_name)
        else:
            raise ValueError("Listener must be callable (a function or method).")

    def remove_listener(self, event_name: str, listener: Callable) -> None:
        """
        Remove a listener from the event.

        :param event_name: Name of the event.
        :param listener: Callable object representing the listener function.
        """
        for event_listener in self._listeners.get(event_name):
            if event_listener.callback == listener:
                self._listeners.get(event_name).remove(event_listener)
                return  # To ensure only one instance is removed

    def schedule_task(self, func: Callable, exc_time: float, *args) -> None:
        if not self._is_event_loop_running:
            raise Exception("No event loop running")

        time_handler = self._loop.call_later(exc_time, func, *args)

        self._time_until_final_task = time_handler.when()

    def cancel_future_sync_event(self, event_name: str) -> None:
        if self._sync_canceled_future_events.get(event_name):
            self._sync_canceled_future_events[event_name] += 1
        else:
            self._sync_canceled_future_events[event_name] = 1

    def cancel_async_event(self, event_name: str) -> None:
        for task in self._running_async_tasks.get(event_name, []):
            try:
                task.cancel()
            except asyncio.CancelledError:
                print(f"failed to cancel task: {task.get_coro().__name__}")

    def sync_trigger(self, event: Event, *args, **kwargs) -> None:
        """
        Trigger the event and notify all registered listeners.

        :param event: The event to trigger.
        :param args: Additional arguments to pass to listeners.
        :param kwargs: Additional keyword arguments to pass to listeners.
        """
        if not self._is_event_loop_running:
            raise Exception("No event loop running")
        self._is_queue_primed = True
        self._event_queue.put_nowait((self._sync_trigger, event, args, kwargs))

    def _sync_trigger(self, event: Event, *args, **kwargs) -> None:
        """
        Internal method to trigger the event and notify all registered listeners.

        :param event: The event to trigger.
        :param args: Additional arguments to pass to listeners.
        :param kwargs: Additional keyword arguments to pass to listeners.
        """
        if self._cancel_events or self._event_cancellation_handler(event):
            return

        responses = 0
        for listener in self._listeners.get(event.event_name, []):
            if event.max_responders != EventDispatcher.UNLIMITED_RESPONDERS and responses >= event.max_responders:
                return

            self._run_sync_listener(listener, event, *args, **kwargs)
            responses += 1

    def _run_sync_listener(self, listener: EventListener, event: Event, *args, **kwargs):
        if self.debug_mode:
            self._log_listener_call(listener, event, False)

        listener.callback(event, *args, **kwargs)

    async def async_trigger(self, event: Event, *args: Any, **kwargs: Any) -> None:
        """
        Asynchronously trigger the event and notify registered listeners.

        :param event: The event to trigger.
        :param args: Additional arguments to pass to listeners.
        :param kwargs: Additional keyword arguments to pass to listeners.
        """
        if not self._is_event_loop_running:
            raise Exception("No event loop running")

        self._is_queue_primed = True
        self._event_queue.put_nowait((self._async_trigger, event, args, kwargs))

    def async_trigger_nw(self, event: Event, *args: Any, **kwargs: Any) -> None:
        """
        Asynchronously trigger the event and notify registered listeners without waiting.

        :param event: The event to trigger.
        :param args: Additional arguments to pass to listeners.
        :param kwargs: Additional keyword arguments to pass to listeners.
        """
        if not self._is_event_loop_running:
            raise Exception("No event loop running")

        self._is_queue_primed = True
        self._event_queue.put_nowait((self._async_trigger, event, args, kwargs))

    async def mixed_trigger(self, event: Event, *args, **kwargs):
        """
       Asynchronously trigger the event and notify registered sync and async listeners

       :param event: The event to trigger.
       :param args: Additional arguments to pass to listeners.
       :param kwargs: Additional keyword arguments to pass to listeners.
       """

        if self._cancel_events or self._event_cancellation_handler(event):
            return

        listeners = self._listeners.get(event.event_name, [])
        self._is_queue_primed = True

        for listener in listeners:
            if asyncio.iscoroutinefunction(listener.callback):
                await self._run_async_listener(listener, event, *args, **kwargs)
            else:
                self._run_sync_listener(listener, event, *args, **kwargs)

    async def _async_trigger(self, event: Event, *args: Any, **kwargs: Any) -> None:
        """
        Internal method to asynchronously trigger the event and notify registered listeners.

        :param event: The event to trigger.
        :param args: Additional arguments to pass to listeners.
        :param kwargs: Additional keyword arguments to pass to listeners.
        """
        if self._cancel_events:
            return

        listeners = self._listeners.get(event.event_name, [])

        # Determine the maximum number of responders to process.
        # If event.max_responders is not set to an unlimited amount of responders,
        # use the max_responders value specified in the event. Otherwise, set the
        # value to the total number of listeners for this event.
        max_responders = event.max_responders if event.max_responders != EventDispatcher.UNLIMITED_RESPONDERS else len(
            listeners)

        callable_listeners = []
        for event_listener in listeners:
            if event_listener.allow_busy_trigger or event_listener.callback not in self._busy_listeners or event.include_busy_listeners:
                callable_listeners.append(event_listener)

            if event_listener.callback not in self._busy_listeners:
                self._busy_listeners.add(event_listener.callback)

        # Asynchronously execute listeners for the event.
        await asyncio.gather(
            *[self._run_async_listener(listener, event, *args, **kwargs) for listener in callable_listeners[:max_responders]]
        )

    async def _run_async_listener(self, listener: EventListener, event: Event, *args, **kwargs):
        """
        Asynchronously run the specified listener for the given event.

        :param listener: The listener to run.
        :param event: The event being processed.
        :param args: Additional arguments to pass to the listener.
        :param kwargs: Additional keyword arguments to pass to the listener.
        """
        if self.debug_mode:
            self._log_listener_call(listener, event, True)

        task = self._event_loop.create_task(listener.callback(event, *args, **kwargs))

        if self._running_async_tasks.get(event.event_name):
            self._running_async_tasks[event.event_name].append(task)
        else:
            self._running_async_tasks[event.event_name] = [task]

        callback = functools.partial(self._clean_up_async_task, event, listener, task)
        task.add_done_callback(callback)

    def _clean_up_async_task(self, event: Event, listener: EventListener,  task: Task, future: Future):
        if listener.callback in self._busy_listeners:
            self._busy_listeners.remove(listener.callback)

        if self._running_async_tasks.get(event.event_name):
            self._running_async_tasks[event.event_name].remove(task)

        if len(self._running_async_tasks.get(event.event_name)) == 0:
            self._running_async_tasks.pop(event.event_name)

    def disable_all_events(self) -> None:
        """
        Disable all events from being triggered.
        """
        self._cancel_events = True

    def enable_all_events(self) -> None:
        """
        Enable all events to be triggered.
        """
        self._cancel_events = False

    def is_queue_empty(self) -> bool:
        """
        Check if the event queue is empty.

        :return: True if the event queue is empty, False otherwise.
        """
        return self._event_queue.empty()

    def queue_size(self) -> int:
        """
        Get the size of the event queue.

        :return: The number of events in the queue.
        """
        return self._event_queue.qsize()

    def get_busy_listeners(self) -> Set[Coroutine]:
        return self._busy_listeners

    def _register_event_listener(self, event_name: str, callback: Callable, priority: Priority, allow_busy_trigger: bool = True) -> None:
        """
        Register an event listener for the specified event.

        :param allow_busy_trigger: allow the listener to be trigger even if it's still running
        :param event_name: Name of the event.
        :param callback: Callable object representing the listener function.
        :param priority: Priority of the listener.
        """
        listener = EventListener(callback=callback, priority=priority, allow_busy_trigger=allow_busy_trigger)

        # if the callback is already registered in the event, return
        if listener.callback in [lstener for lstener in self._listeners.get(event_name, [])]:
            return

        if event_name in self._listeners:
            self._listeners[event_name].append(listener)
        else:
            self._listeners.update({event_name: [listener]})

    def _sort_listeners(self, event_name: str) -> None:
        """
        Sort the listeners for the specified event based on their priorities.

        :param event_name: Name of the event.
        """
        if event_name not in self._listeners:
            return
        self._listeners[event_name] = sorted(self._listeners[event_name],
                                             key=lambda event_listener: event_listener.priority.value)

    def _log_listener_call(self, listener: EventListener, event: Event, is_async: bool) -> None:
        """
        Log the invocation of an event listener, including whether it's synchronous or asynchronous.

        :param listener: The event listener being invoked.
        :param event: The event associated with the listener.
        :param is_async: True if the listener is asynchronous; False if synchronous.
        """
        message_front = "async calling" if is_async else "calling"

        logging.info(f"{message_front}: [{listener.callback.__name__}] from event: [{event.event_name}]")

        if is_async and listener.callback in self._busy_listeners:
            logging.info(f"skipping call to: [{listener.callback.__name__}] as it's busy")

    def _set_event_loop(self, loop: asyncio.AbstractEventLoop) -> AbstractEventLoop:
        """
        Set the event loop, creating a new one if needed.
        """
        if not loop:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        else:
            self._loop = loop

        return self._loop

    def _event_cancellation_handler(self, event: Event) -> bool:
        # if the event has not been canceled at least once return false
        if not self._sync_canceled_future_events.get(event.event_name, 0):
            return False

        self._sync_canceled_future_events[event.event_name] -= 1

        # remove the event data from the dict
        if self._sync_canceled_future_events[event.event_name] < 1:
            self._sync_canceled_future_events.pop(event.event_name)
        return True

    async def _event_loop_runner(self):
        """
        Run the event loop to process queued events.
        """

        while self._is_event_loop_running:
            queue_item: Tuple[Union[Callable, Coroutine], Event, Any, Any] = await self._event_queue.get()
            event_executor, event, args, kwargs = queue_item

            if asyncio.iscoroutinefunction(event_executor):
                task = self._event_loop.create_task(event_executor(event, *args, **kwargs))
                if callable(event.on_finish): task.add_done_callback(event.on_finish)
            else:
                # For synchronous functions, use asyncio.to_thread to run them in a separate thread
                await asyncio.to_thread(event_executor, event, *args, **kwargs)
                if callable(event.on_finish): event.on_finish()

            # if the queue is empty set the empty event (true)
            if self._event_queue.empty():
                self._queue_empty_event.set()
            # else clear the event (false)
            else:
                self._queue_empty_event.clear()

            self._event_queue.task_done()
