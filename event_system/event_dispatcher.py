import asyncio
import functools
import logging
import os

from asyncio import AbstractEventLoop, Task, Future
from typing import Callable, Any, Set, List, Dict, Union, Coroutine, Tuple, Generator

from .event_listener import EventListener, Priority
from .event import Event
from .event_type import EventType
from .executor import Executor


class EventDispatcher:
    """
    EventDispatcher handles event listeners, triggers events, and manages asynchronous execution of listeners.
    """
    UNLIMITED_RESPONDERS = -1

    def __init__(
            self,
            loop: asyncio.AbstractEventLoop = None,
            use_threaded_executor: bool = True,
            max_executor_workers: int = -1,
            debug_mode: bool = False,
    ):
        """
        Initialize the EventDispatcher.

        :param loop: The event loop to use. If not provided, try to get the existing loop.
                     If all fails it creates a new event loop.
        :param debug_mode: Enable debug mode for logging.
        :param use_threaded_executor: Flag to choose between using a threaded or process-based executor.
                                      Defaults to using a threaded executor (ThreadPoolExecutor).
        :param max_executor_workers: The maximum number of workers for the underlying executor.
                                     Defaults to -1 which uses the available logical CPU count.
        """
        self.debug_mode = debug_mode

        self._listeners: Dict[str, List['EventListener']] = {}
        self._sync_canceled_future_events: Dict[str, int] = {}
        self._busy_listeners: Set[Coroutine] = set()

        # Event loop and related components
        self._event_queue_manager_task: Task = None  # noqa
        self._event_loop = self._set_event_loop(loop)
        self._event_queue = asyncio.Queue()
        self._queue_empty_event = asyncio.Event()  # Event signaling an empty queue

        # Dictionary to hold running tasks
        self._running_tasks: Dict[str, List[Union[Task, Future]]] = {}
        self._time_until_final_task = 0  # Time until the final task is complete

        # Flags for controlling event dispatch and queue status
        self._cancel_events = False
        self._is_queue_primed = False
        self._is_event_loop_running = False

        # Determine the total number of workers based on available logical cores
        cpu_count = os.cpu_count()
        total_logical_cores = cpu_count if cpu_count else 1
        total_workers = max_executor_workers if max_executor_workers != -1 else total_logical_cores

        # Initialize the executor for handling asynchronous tasks
        self._executor = Executor(max_workers=total_workers)

    def start(self):
        """
        Start the event loop if not already running.
        """
        if not self._is_event_loop_running:
            self._event_queue_manager_task = self._event_loop.create_task(self._event_loop_runner())
            self._is_event_loop_running = True

    async def close(self, wait_for_scheduled_tasks: bool = True):
        """
        Close the event loop and wait for queued and scheduled events to be processed.

        :param wait_for_scheduled_tasks: Flag to indicate whether to wait for scheduled tasks to complete.
        """
        try:
            if self._is_queue_primed:
                # Wait for all events in the queue to be processed
                await self._queue_empty_event.wait()
            else:
                # If no events have been placed in the queue, cancel the task to avoid indefinite waiting
                self._event_queue_manager_task.cancel('Canceling queue manager due to no events to process')

            if wait_for_scheduled_tasks:
                # Calculate the time left until the final task is complete
                final_task_complete_time = self._time_until_final_task - self._loop.time()
                # Ensure the value is positive or zero(z)
                z_final_task_complete_time = final_task_complete_time if final_task_complete_time > 0 else 0
                await asyncio.sleep(z_final_task_complete_time)

            submitted_futures = self._executor.get_running_futures()
            # all futures and tasks that have been created are collected here
            waitables_collection: Dict[AbstractEventLoop, List[Union[Task, Future]]] = {}

            # here we collect all the running tasks (async Events)
            for _, running_tasks in self._running_tasks.items():
                for task in running_tasks:
                    if task.cancelled() or task.done():
                        continue
                    loop = task.get_loop()

                    if waitables_collection.get(loop):
                        waitables_collection[loop].append(task)
                    else:
                        waitables_collection[loop] = [task]

            # here we collect all the futures (sync Events)
            for loop, futures in submitted_futures.items():
                running_futures = [future for future in futures if not (future.cancelled() and future.done())]

                if waitables_collection.get(loop):
                    waitables_collection[loop].extend(*running_futures)
                else:
                    waitables_collection[loop] = running_futures

            # wait for the completion of the varius tasks and futures running based on their loop
            for loop, waitables in waitables_collection.items():
                print(waitables)
                await asyncio.gather(*waitables)

            self._executor.shutdown()

        except Exception as e:
            # this is temp and for debugging
            print(e)
            raise

        self._is_event_loop_running = False

    def add_listener(self, event_name: str, listener: Callable, priority: Priority = Priority.NORMAL,
                     allow_busy_trigger: bool = True, event_type: EventType = EventType.Base) -> None:
        """
        Add a listener to the event.

        :param event_type: the type of event to respond to, EventType.Base responds to all types
        :param allow_busy_trigger: allow the listener to be trigger even if it's still running
        :param event_name: Name of the event.
        :param listener: Callable object representing the listener function.
        :param priority: Priority of the listener.
        """
        if callable(listener):
            self._register_event_listener(event_name, listener, priority, allow_busy_trigger, event_type)
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
        """
        Schedule a task to be executed after a specified delay.

        This method schedules a callable function (`func`) to be executed after a specified time (`exc_time`) on the
        event loop. The `func` will be called with the provided arguments (`*args`) when the scheduled time is reached.

        :param func: The function or callable to be executed.
        :param exc_time: The time in seconds after which the function will be called.
        :param args: Additional arguments to pass to the function.
        :raises Exception: If there is no event loop running when attempting to schedule the task.
        """
        if not self._is_event_loop_running:
            raise Exception("No event loop running")

        time_handler = self._loop.call_later(exc_time, func, *args)

        self._time_until_final_task = time_handler.when()

    def cancel_future_sync_event(self, event_name: str) -> None:
        """
        Cancel future occurrences of a synchronous event.

        This method increments the cancellation count for a specific synchronous event (`event_name`). It keeps track of
        the number of times the event has been canceled to prevent its future execution based on the cancellation count.

        If the event has already been canceled at least once, this method increments the cancellation count. Otherwise,
        it initializes the count to 1.

        :param event_name: The name or identifier of the synchronous event to cancel.
        """
        if self._sync_canceled_future_events.get(event_name):
            self._sync_canceled_future_events[event_name] += 1
        else:
            self._sync_canceled_future_events[event_name] = 1

    def cancel_event(self, event_name: str) -> None:
        """
        Cancel all running tasks associated with a specific event.

        This method cancels all running asynchronous tasks that are associated with a given event (`event_name`). It
        retrieves the tasks related to the specified event and attempts to cancel each task.

        :param event_name: The name or identifier of the event for which running asynchronous tasks should be canceled.
        """
        for task in self._running_tasks.get(event_name, []):
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
        max_responders = event.max_responders if event.max_responders != EventDispatcher.UNLIMITED_RESPONDERS else float('inf')

        for listener in self._get_listeners(event):
            if responses >= max_responders:
                return

            self._run_sync_listener(listener, event, *args, **kwargs)
            responses += 1

        if event.on_event_finish:
            try:
                self._safe_run_callable(event.on_event_finish)
            except RuntimeWarning:
                raise Exception("on finish callbacks can only be sync in a sync context")

    def _run_sync_listener(self, listener: EventListener, event: Event, *args, **kwargs):
        """
        Execute a synchronous event listener.

        This method executes a synchronous event listener represented by the provided `listener` object, passing the
        associated event (`event`) along with additional arguments and keyword arguments.

        If debug mode is enabled (`self.debug_mode`), it logs the invocation of the listener.

        :param listener: The EventListener representing the synchronous event listener function to execute.
        :param event: The event associated with the listener.
        :param args: Additional arguments to pass to the listener.
        :param kwargs: Additional keyword arguments to pass to the listener.
        """
        if self.debug_mode:
            self._log_listener_call(listener, event, False)
        try:

            future = self._executor.submit(listener.callback, event, *args, **kwargs)

            if callable(event.on_listener_finish):
                future.add_done_callback(event.on_listener_finish)

        except Exception as e:
            print(e)

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

        self._is_queue_primed = True

        for listener in self._get_listeners(event):
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

        callable_listeners = [event_listener for event_listener in self._get_listeners(event)
                              if
                              (event_listener.allow_busy_trigger or event_listener.callback not in self._busy_listeners
                               or event.include_busy_listeners)]

        for event_listener in callable_listeners:
            if event_listener.callback not in self._busy_listeners:
                self._busy_listeners.add(event_listener.callback)

        listeners_to_execute = callable_listeners[:max_responders]

        tasks = [self._run_async_listener(listener, event, *args, **kwargs) for listener in listeners_to_execute]

        if event.on_event_finish:
            await self._safe_run_callable(event.on_event_finish)

        await asyncio.gather(*tasks)

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

        if event.on_listener_finish:
            task.add_done_callback(event.on_listener_finish)

        self._add_task_to_running_tasks(task, event)

        cleanup = functools.partial(self._clean_up_tracked_task, event, listener, task)
        task.add_done_callback(cleanup)

    def _clean_up_tracked_task(self, event: Event, listener: EventListener, task: Task, future: Future):
        if listener.callback in self._busy_listeners:
            self._busy_listeners.remove(listener.callback)

        if self._running_tasks.get(event.event_name):
            self._running_tasks[event.event_name].remove(task)

        if len(self._running_tasks.get(event.event_name)) == 0:
            self._running_tasks.pop(event.event_name)

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

    @staticmethod
    def _does_event_type_match(listener: EventListener, event: Event) -> bool:
        if listener.event_type == EventType.Base or listener.event_type == event.event_type:
            return True

        return False

    @staticmethod
    async def _safe_run_callable(func: Union[Callable, Coroutine], *args, **kwargs) -> None:
        if not callable(func):
            return

        if asyncio.iscoroutinefunction(func):
            await func(*args, **kwargs)
        else:
            func(*args, **kwargs)

    def _get_listeners(self, event: Event) -> Generator[EventListener, None, None]:
        for listener in self._listeners.get(event.event_name, []):
            if not self._does_event_type_match(listener, event):
                continue
            yield listener

    def _register_event_listener(self, event_name: str, callback: Callable, priority: Priority,
                                 allow_busy_trigger: bool = True, event_type: EventType = EventType.Base) -> None:
        """
        Register an event listener for the specified event.

        :param allow_busy_trigger: allow the listener to be trigger even if it's still running
        :param event_name: Name of the event.
        :param callback: Callable object representing the listener function.
        :param priority: Priority of the listener.
        """
        listener = EventListener(callback=callback, priority=priority, allow_busy_trigger=allow_busy_trigger,
                                 event_type=event_type)

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
        message_front = "calling async" if is_async else "calling sync"

        logging.info(f"{message_front} listener: [{listener.callback.__name__}] from event: [{event.event_name}]")

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

    def _add_task_to_running_tasks(self, task: Union[Task, Future], event: Event) -> None:
        if self._running_tasks.get(event.event_name):
            self._running_tasks[event.event_name].append(task)
        else:
            self._running_tasks[event.event_name] = [task]

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
                self._event_loop.create_task(event_executor(event, *args, **kwargs))
            else:
                # here it will run self._sync_trigger
                event_executor(event, *args, **kwargs)

            # if the queue is empty set the empty event (true)
            if self._event_queue.empty():
                self._queue_empty_event.set()
            # else clear the event (false)
            else:
                self._queue_empty_event.clear()

            self._event_queue.task_done()
