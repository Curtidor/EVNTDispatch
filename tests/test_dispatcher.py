import unittest

from EVNTDispatch import EventDispatcher, EventType, PEvent


class TestDispatcher(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.dispatcher = EventDispatcher(debug_mode=True)
        self.dispatcher.start()

    async def test_scheduling_wait_for_greatest_time(self):
        """
        Test scheduling tasks and waiting for the task with the greatest time delay.

        This test schedules two tasks using the EventDispatcher instance:
        - listener_one with a delay of 0.7 seconds
        - listener_two with a delay of 0.05 seconds

        It then waits for all scheduled tasks to complete by closing the dispatcher with wait_for_scheduled_tasks=True.
        Afterward, it asserts that both listeners were executed, resulting in a total of 2 responses.
        """
        responses = 0

        def listener_one():
            nonlocal responses
            responses += 1

        def listener_two():
            nonlocal responses
            responses += 1

        self.dispatcher.schedule_task(listener_one, 0.7)
        self.dispatcher.schedule_task(listener_two, 0.05)

        await self.dispatcher.close(wait_for_scheduled_tasks=True)

        self.assertEqual(2, responses)

    async def test_get_listeners(self):
        """
        Test the retrieval of listeners based on event types.

        This test adds multiple listeners to the 'test' event of different types using lambda functions.
        It then creates several PEvent instances with varying event types and max_responders values,
        and verifies that the correct number of listeners are retrieved for each event type.

        - EventType.UserInteraction: Asserts 1 listener for event_one, 2 listeners for event_two, and 3 listeners for event_max.
        - EventType.NetworkEvent: Asserts 1 listener for event_mismatch.
        - EventType.Base: Asserts 4 listeners for event_neg.

        It uses assertions to ensure the correct number of listeners are retrieved for each event type.
        """
        self.dispatcher.add_listener('test', lambda a, b: a + b, event_type=EventType.UserInteraction)
        self.dispatcher.add_listener('test', lambda a, b: a + b, event_type=EventType.UserInteraction)
        self.dispatcher.add_listener('test', lambda a, b: a + b, event_type=EventType.UserInteraction)
        self.dispatcher.add_listener('test', lambda a, b: a + b, event_type=EventType.NetworkEvent)

        event_one = PEvent('test', EventType.UserInteraction, max_responders=1)
        event_two = PEvent('test', EventType.UserInteraction, max_responders=2)
        event_max = PEvent('test', EventType.UserInteraction, max_responders=9999)
        event_neg = PEvent('test', EventType.Base, max_responders=-9999)
        event_mismatch = PEvent('test', EventType.NetworkEvent, max_responders=999)

        self.assertEqual(1, len([listener for listener in self.dispatcher._get_listeners(event_one)]))
        self.assertEqual(2, len([listener for listener in self.dispatcher._get_listeners(event_two)]))
        self.assertEqual(3, len([listener for listener in self.dispatcher._get_listeners(event_max)]))
        self.assertEqual(4, len([listener for listener in self.dispatcher._get_listeners(event_neg)]))
        self.assertEqual(1, len([listener for listener in self.dispatcher._get_listeners(event_mismatch)]))


if __name__ == '__main__':
    unittest.main()
