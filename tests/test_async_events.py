import asyncio
import time
import unittest

from math import isclose

from event_system.event_dispatcher import EventDispatcher
from event_system.pevent import PEvent
from event_system.event_listener import Priority
from event_system.event_type import EventType


class TestAsyncEventDispatcher(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """
        Setup method to initialize the EventDispatcher before each tests.
        """
        self.event_dispatcher = EventDispatcher(debug_mode=True)
        self.event_dispatcher.start()

    async def test_async_busy_listeners_handling(self):
        """
        Test EventDispatcher handling of asynchronous listeners.

        Verifies that the EventDispatcher can handle multiple asynchronous event listeners attached to the same event,
        ensuring proper execution even when some listeners are busy with time-consuming tasks.
        """
        listener_one_results = []
        listener_two_results = []

        async def listener_one(event):
            await asyncio.sleep(2)
            listener_one_results.append("success")

        async def listener_two(event):
            listener_two_results.append("success")

        self.event_dispatcher.add_listener("tests", listener_one, allow_busy_trigger=False)
        self.event_dispatcher.add_listener("tests", listener_two)

        await self.event_dispatcher.async_trigger(PEvent("tests", EventType.Base))
        await self.event_dispatcher.async_trigger(PEvent("tests", EventType.Base))

        await self.event_dispatcher.close()

        self.assertEqual(["success"], listener_one_results)
        self.assertEqual(["success", "success"], listener_two_results)

    async def test_max_responders_and_priority_handling(self):
        """
        Test EventDispatcher handling of max responders and listener priorities.

        Verifies that the EventDispatcher correctly handles max responders and listener priorities.
        """
        listener_one_results = []
        listener_two_results = []

        async def listener_one(event):
            listener_one_results.append("success")

        async def listener_two(event):
            listener_two_results.append("success")

        self.event_dispatcher.add_listener("tests", listener_one, priority=Priority.NORMAL)
        self.event_dispatcher.add_listener("tests", listener_two, priority=Priority.HIGH)

        await self.event_dispatcher.async_trigger(PEvent("tests", EventType.Base, max_responders=1))

        await self.event_dispatcher.close()

        self.assertEqual(listener_one_results, [])
        self.assertEqual(listener_two_results, ["success"])

    async def test_register_listener_with_same_name_as_busy_listener(self):
        """
        Test registering a listener with the same name as a busy listener.

        Verifies that registering a callback with the same name as a busy listener under a different event works as expected.
        """
        collected_data = []

        async def listener_one(event: PEvent):
            await asyncio.sleep(1.5)
            collected_data.append('s')

        self.event_dispatcher.add_listener("tests 1", listener_one)
        await self.event_dispatcher.async_trigger(PEvent("tests 1", EventType.Base))

        self.event_dispatcher.add_listener("tests 2", listener_one, allow_busy_trigger=False)
        await self.event_dispatcher.async_trigger(PEvent("tests 2", EventType.Base))

        await self.event_dispatcher.close()

        self.assertEqual(1, len(collected_data))

    async def test_schedule_task(self):
        """
        Test scheduling tasks with EventDispatcher.

        Verifies the EventDispatcher's ability to schedule tasks and execute them.
        """
        t = []
        sleep_time = 1

        async def listener_one():
            await asyncio.sleep(1)
            t.append(time.time())

        delay = 2
        start_time = time.time()

        self.event_dispatcher.schedule_task(listener_one, delay)

        await self.event_dispatcher.close()

        try:
            end_time = t[0]
        except IndexError:
            self.fail('scheduled task was not ran')

        self.assertTrue(isclose((end_time - start_time), delay + sleep_time, abs_tol=0.35))

    async def test_on_finish_callback(self):
        """
        Test waiting for events with EventDispatcher.

        Verifies the EventDispatcher's functionality of correctly triggering the finish callback when the event is finished
        """
        event_done = asyncio.Event()

        def event_set_callback(fut):
            event_done.set()

        collected_data = []
        VERIFICATION_VALUE = '1'

        SLEEP_VALUE = 1.5
        ERROR_VALUE = 0.8

        async def listener_one(event: PEvent):
            collected_data.append(VERIFICATION_VALUE)
            await asyncio.sleep(SLEEP_VALUE)

        self.event_dispatcher.add_listener('tests', listener_one)
        await self.event_dispatcher.async_trigger(PEvent('tests', EventType.Base, on_listener_finish=event_set_callback))

        try:
            await asyncio.wait_for(event_done.wait(), SLEEP_VALUE + ERROR_VALUE)
        except asyncio.TimeoutError:
            self.fail("The on finish call back was not triggered!")

        await self.event_dispatcher.close()

        self.assertEqual('1', collected_data[0])

    async def test_cancel_running_async_event(self):
        collected_values = []

        async def listener_one(event):
            await asyncio.sleep(1.3)
            collected_values.append('1')

        self.event_dispatcher.add_listener('tests', listener_one)
        await self.event_dispatcher.async_trigger(PEvent('tests', EventType.Base))

        await asyncio.sleep(1)
        self.event_dispatcher.cancel_event('tests')

        await self.event_dispatcher.close()

        self.assertEqual(0, len(collected_values))


if __name__ == "__main__":
    unittest.main()
