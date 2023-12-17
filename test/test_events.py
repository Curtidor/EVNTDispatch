import time
import unittest

from event_system.event_dispatcher import EventDispatcher, Event
from event_system.event_type import EventType


class TestEvents(unittest.IsolatedAsyncioTestCase):
    async def test_add_listener_before_event_creation(self):
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        listener_one_responses = []

        def listener_one(event: Event):
            listener_one_responses.append("success")

        event_dispatcher.add_listener("test", listener_one)
        event_dispatcher.trigger(Event("test", EventType.Base))

        await event_dispatcher.close()

        self.assertEqual(["success"], listener_one_responses)

    async def test_schedule_task(self):
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        start_time = time.time()
        t = []

        def listener_one():
            t.append(time.time())

        delay = 2

        event_dispatcher.schedule_task(listener_one, delay)
        event_dispatcher.trigger(Event("test", EventType.Base))
        await event_dispatcher.close()

        end_time = t[0]
        self.assertTrue(round(end_time - start_time) == delay)


if __name__ == '__main__':
    unittest.main()
