import asyncio
import time
import unittest

from event_system.event_dispatcher import EventDispatcher
from event_system.event import Event
from event_system.event_listener import Priority
from event_system.event_type import EventType


class TestSyncEventDispatcher(unittest.IsolatedAsyncioTestCase):

    async def test_add_listener_before_event_creation(self):
        """
        Test adding a listener before event creation.

        Verifies that adding a listener before triggering an event in the EventDispatcher
        leads to the listener being executed when the event is triggered.
        """
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        listener_one_responses = []

        def listener_one(event: Event):
            listener_one_responses.append("success")

        event_dispatcher.add_listener("test", listener_one)
        event_dispatcher.sync_trigger(Event("test", EventType.Base))

        await event_dispatcher.close()

        self.assertEqual(["success"], listener_one_responses)

    async def test_schedule_task(self):
        """
        Test scheduling a task with EventDispatcher.

        Verifies that EventDispatcher can schedule a task and execute it after a specified delay.
        """
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        t = []

        def listener_one():
            t.append(time.time())

        delay = 2
        start_time = time.time()

        event_dispatcher.schedule_task(listener_one, delay)

        await event_dispatcher.close()

        end_time = t[0]
        self.assertTrue(round(end_time - start_time) == delay)

    async def test_wait_for_event(self) -> None:
        """
        Test waiting for events with EventDispatcher.

        Verifies the EventDispatcher's functionality for waiting on events and executing associated callbacks upon finishing the event.
        """
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        event_done = asyncio.Event()

        def event_set_callback():
            event_done.set()

        collected_data = []
        VERIFICATION_VALUE = '1'

        SLEEP_VALUE = 1.5
        ERROR_VALUE = 0.8

        def listener_one(event: Event):
            time.sleep(SLEEP_VALUE)
            collected_data.append(VERIFICATION_VALUE)

        event_dispatcher.add_listener('test', listener_one)
        event_dispatcher.sync_trigger(Event('test', EventType.Base, on_finish=event_set_callback))

        try:
            await asyncio.wait_for(event_done.wait(), SLEEP_VALUE + ERROR_VALUE)
        except asyncio.TimeoutError:
            self.fail("The on finish call back was not triggered!")

        self.assertEqual('1', collected_data[0])

        await event_dispatcher.close()

    async def test_cancel_event(self) -> None:
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        listener_one_results = []
        listener_two_results = []

        async def listener_one(event: Event):
            await asyncio.sleep(3)
            listener_one_results.append('1')

        def listener_two(event: Event):
            listener_two_results.append('2')

        event_dispatcher.add_listener('test', listener_one, priority=Priority.NORMAL)
        event_dispatcher.add_listener('test', listener_two, priority=Priority.HIGH)

        event_dispatcher.cancel_future_sync_event('test')

        await event_dispatcher.mixed_trigger(Event('test', EventType.Base))

        self.assertEqual([], listener_two_results)
        self.assertEqual([], listener_two_results)


if __name__ == '__main__':
    unittest.main()
