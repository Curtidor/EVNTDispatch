import asyncio
import unittest

from event_system.event_dispatcher import EventDispatcher
from event_system.event import Event
from event_system.event_listener import Priority
from event_system.event_type import EventType


class TestAsyncEventDispatcher(unittest.IsolatedAsyncioTestCase):

    async def test_async_busy_listeners_handling(self):
        """
        Test EventDispatcher handling of asynchronous listeners.

        Verifies that the EventDispatcher can handle multiple asynchronous event listeners attached to the same event,
        ensuring proper execution even when some listeners are busy with time-consuming tasks.
        """
        # Initialize empty lists to store results from event listeners
        listener_one_results = []
        listener_two_results = []

        event_dispatcher = EventDispatcher(debug_mode=True)
        event_dispatcher.start()

        async def listener_one(event):
            await asyncio.sleep(2)
            # Simulate some asynchronous work by waiting for 0.3 seconds
            listener_one_results.append("success")

        async def listener_two(event):
            listener_two_results.append("success")

        # Add both listeners to the same event ("test") in the EventDispatcher
        event_dispatcher.add_listener("test", listener_one, allow_busy_trigger=False)
        event_dispatcher.add_listener("test", listener_two)

        # Trigger the event twice asynchronously using async_trigger
        await event_dispatcher.async_trigger(Event("test", EventType.Base))
        await event_dispatcher.async_trigger(Event("test", EventType.Base))

        await event_dispatcher.close()

        # Assert listener_one has been called only once due to the 0.3-second delay,
        # and listener_two has been called twice (once for each event trigger)
        self.assertEqual(["success"], listener_one_results)
        self.assertEqual(["success", "success"], listener_two_results)

    async def test_max_responders_and_priority_handling(self):
        """
        Test EventDispatcher handling of max responders and listener priorities.

        Verifies that the EventDispatcher correctly handles max responders and listener priorities.
        """
        # Initialize empty lists to store results from event listeners
        listener_one_results = []
        listener_two_results = []

        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        # Define two asynchronous event listeners (listener_one and listener_two)
        async def listener_one(event):
            # high
            listener_one_results.append("success")

        async def listener_two(event):
            # normal
            listener_two_results.append("success")

        # Add both listeners to the same event ("test") in the EventDispatcher with specified priorities
        event_dispatcher.add_listener("test", listener_one, priority=Priority.HIGH)
        event_dispatcher.add_listener("test", listener_two, priority=Priority.NORMAL)

        # Trigger the event asynchronously with max_responders=1
        await event_dispatcher.async_trigger(Event("test", EventType.Base, max_responders=1))
        await event_dispatcher.close()

        # Assert only the highest priority listener (listener_one) has been called,
        # and the second listener (listener_two) has not been executed due to max_responders=1
        self.assertEqual(listener_one_results, ["success"])
        self.assertEqual(listener_two_results, [])

    async def test_register_listener_with_same_name_as_busy_listener(self):
        """
        Test registering a listener with the same name as a busy listener.

        Verifies that registering a callback with the same name as a busy listener under a different event works as expected.
        """
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        collected_data = []

        async def listener_one(event: Event):
            await asyncio.sleep(1.5)
            collected_data.append('s')

        event_dispatcher.add_listener("test 1", listener_one)
        # trigger listen_one with event (test 1)
        await event_dispatcher.async_trigger(Event("test 1", EventType.Base))

        # register the same callback under a different event
        event_dispatcher.add_listener("test 2", listener_one, allow_busy_trigger=False)
        # trigger listen_one with event (test 2)
        await event_dispatcher.async_trigger(Event("test 2", EventType.Base))

        await event_dispatcher.close()
        self.assertEqual(1, len(collected_data))

    async def test_schedule_task(self):
        """
        Test scheduling tasks with EventDispatcher.

        Verifies the EventDispatcher's ability to schedule tasks and execute them.
        """
        pass  # Implement test logic for scheduling tasks

    async def test_on_finish_callback(self):
        """
        Test waiting for events with EventDispatcher.

        Verifies the EventDispatcher's functionality of correctly triggering the finish callback when the event is finished
        """
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        event_done = asyncio.Event()

        def event_set_callback(fut):
            event_done.set()

        collected_data = []
        VERIFICATION_VALUE = '1'

        SLEEP_VALUE = 1.5
        ERROR_VALUE = 0.8

        async def listener_one(event: Event):
            collected_data.append(VERIFICATION_VALUE)
            await asyncio.sleep(SLEEP_VALUE)

        event_dispatcher.add_listener('test', listener_one)
        await event_dispatcher.async_trigger(Event('test', EventType.Base, on_finish=event_set_callback))

        try:
            await asyncio.wait_for(event_done.wait(), SLEEP_VALUE + ERROR_VALUE)
        except asyncio.TimeoutError:
            self.fail("The on finish call back was not triggered!")

        self.assertEqual('1', collected_data[0])


if __name__ == "__main__":
    unittest.main()
