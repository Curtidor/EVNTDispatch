import asyncio
import unittest
import threading

from EVNTDispatch.event_dispatcher import EventDispatcher, Priority
from EVNTDispatch.pevent import PEvent
from EVNTDispatch.event_type import EventType


class TestSyncThreadingEventDispatcher(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up the EventDispatcher for each test."""
        self.event_dispatcher = EventDispatcher(debug_mode=True)
        self.event_dispatcher.start()

    async def test_threading_with_busy_listeners(self):
        """
        Test the event system with busy and non-busy listeners.

        This test ensures that the event system correctly handles listeners that
        are busy when the event is triggered. The busy listener (listener_one) is
        expected to be skipped due to the allow_busy_trigger=False setting. The
        non-busy listener (listener_two) should respond to all triggers.

        The test uses threading to simulate concurrent event triggering and
        verifies that the total number of responses is as expected.
        """
        responses = 0

        async def listener_one(event_c: PEvent):
            await asyncio.sleep(0.65)
            nonlocal responses
            responses += 1

        async def listener_two(event_c: PEvent):
            nonlocal responses
            responses += 1

        self.event_dispatcher.add_listener('test', listener_one, allow_busy_trigger=False)
        self.event_dispatcher.add_listener('test', listener_two)

        event = PEvent('test', EventType.Base, include_busy_listeners=False)

        t1 = threading.Thread(target=self.event_dispatcher.async_trigger_nw(event))
        t2 = threading.Thread(target=self.event_dispatcher.async_trigger_nw(event))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        await self.event_dispatcher.close()

        self.assertEqual(3, responses)

    async def test_concurrent_events_with_shared_listeners(self):
        """
        Test concurrent event triggering with shared listeners.

        This test validates that the event system correctly handles concurrent
        events with listeners that are shared across multiple events. It ensures
        that each listener responds appropriately to the events they are registered
        for and that the responses include data specific to each event.

        The test uses threading to simulate concurrent event triggering and
        verifies that all expected responses are received.
        """
        responses = []

        async def shared_listener(event_c: PEvent):
            responses.append(f"shared: {event_c.data}")

        async def unique_listener_one(event_c: PEvent):
            responses.append(f"unique_one: {event_c.data}")

        async def unique_listener_two(event_c: PEvent):
            responses.append(f"unique_two: {event_c.data}")

        self.event_dispatcher.add_listener('event_two', shared_listener)
        self.event_dispatcher.add_listener('event_two', unique_listener_two)
        self.event_dispatcher.add_listener('event_one', shared_listener)
        self.event_dispatcher.add_listener('event_one', unique_listener_one)

        event_one = PEvent('event_one', EventType.Base, data='event_one')
        event_two = PEvent('event_two', EventType.Base, data='event_two')

        t1 = threading.Thread(target=self.event_dispatcher.async_trigger_nw(event_one))
        t2 = threading.Thread(target=self.event_dispatcher.async_trigger_nw(event_two))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        await self.event_dispatcher.close()

        expected_responses = {'shared: event_one', 'unique_one: event_one', 'shared: event_two',
                              'unique_two: event_two'}
        self.assertEqual(set(responses), expected_responses)


if __name__ == '__main__':
    unittest.main()
