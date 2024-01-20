import asyncio
import time
import unittest

from math import isclose

from EVNTDispatch.event_dispatcher import EventDispatcher, Priority
from EVNTDispatch.pevent import PEvent
from EVNTDispatch.event_type import EventType


class TestSyncEventDispatcher(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.event_dispatcher = EventDispatcher(debug_mode=True)
        self.event_dispatcher.start()

    async def test_base_sync_trigger(self):
        """
        Test adding a listener and triggering a sync event
        """
        listener_one_responses = []

        def listener_one(event: PEvent):
            listener_one_responses.append("success")

        self.event_dispatcher.add_listener("tests", listener_one)
        self.event_dispatcher.sync_trigger(PEvent("tests", EventType.Base))

        await self.event_dispatcher.close()

        self.assertEqual(["success"], listener_one_responses)

    async def test_max_responders_and_priority(self):
        listener_one_responses = []
        listener_two_responses = []

        def listener_one(event: PEvent):
            listener_one_responses.append("success")

        def listener_two(event: PEvent):
            listener_two_responses.append("success")

        self.event_dispatcher.add_listener("tests", listener_one, priority=Priority.NORMAL)
        self.event_dispatcher.add_listener("tests", listener_two, priority=Priority.HIGH)

        self.event_dispatcher.sync_trigger(PEvent("tests", EventType.Base, max_responders=1))

        await self.event_dispatcher.close()

        self.assertEqual([], listener_one_responses)
        self.assertEqual(["success"], listener_two_responses)

    async def test_schedule_task(self):
        """
        Test scheduling a task with EventDispatcher.

        Verifies that EventDispatcher can schedule a task and execute it after a specified delay.
        """
        t = []

        def listener_one():
            t.append(time.time())

        delay = 2
        start_time = time.time()

        self.event_dispatcher.schedule_task(listener_one, delay)

        await self.event_dispatcher.close()

        try:
            end_time = t[0]
        except IndexError:
            self.fail('scheduled task was not ran')

        self.assertTrue(isclose((end_time - start_time), delay, abs_tol=0.35))

    async def test_on_listener_finish(self) -> None:
        event_done = asyncio.Event()

        def event_set_callback():
            event_done.set()

        collected_data = []
        VERIFICATION_VALUE = '1'
        TIMEOUT = 2

        def listener_one(event: PEvent):
            collected_data.append(VERIFICATION_VALUE)

        self.event_dispatcher.add_listener('tests', listener_one)
        self.event_dispatcher.sync_trigger(PEvent('tests', EventType.Base, on_listener_finish=event_set_callback))

        try:
            await asyncio.wait_for(event_done.wait(), TIMEOUT)
        except asyncio.TimeoutError:
            self.fail('event was not set')

        self.assertTrue(VERIFICATION_VALUE in collected_data)

        await self.event_dispatcher.close()

    async def test_event_on_finish(self) -> None:
        event_done = asyncio.Event()

        def event_set_callback():
            event_done.set()

        collected_data = []
        VERIFICATION_VALUE = '1'
        TIMEOUT = 2

        def listener_one(event: PEvent):
            collected_data.append(VERIFICATION_VALUE)

        self.event_dispatcher.add_listener('tests', listener_one)
        self.event_dispatcher.sync_trigger(PEvent('tests', EventType.Base, on_event_finish=event_set_callback))

        try:
            await asyncio.wait_for(event_done.wait(), TIMEOUT)
        except asyncio.TimeoutError:
            self.fail('event was not set')

        self.assertTrue(VERIFICATION_VALUE in collected_data)

        await self.event_dispatcher.close()

    async def test_cancel_future_event(self):
        listener_one_responses = []
        listener_two_responses = []

        def listener_one(event: PEvent):
            listener_one_responses.append("item")

        def listener_two(event: PEvent):
            listener_two_responses.append("item")

        self.event_dispatcher.add_listener('tests', listener_one)
        self.event_dispatcher.add_listener('tests', listener_two)

        self.event_dispatcher.cancel_future_sync_event('tests')

        self.event_dispatcher.sync_trigger(PEvent('tests', EventType.Base))

        await self.event_dispatcher.close()

        self.assertEqual([], listener_one_responses)
        self.assertEqual([], listener_two_responses)


if __name__ == '__main__':
    unittest.main()
