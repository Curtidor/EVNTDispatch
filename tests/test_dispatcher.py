import unittest

from EVNTDispatch import EventDispatcher, EventType, PEvent


class TestDispatcher(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.dispatcher = EventDispatcher(debug_mode=True)
        self.dispatcher.start()

    async def test_get_listeners(self):
        self.dispatcher.add_listener('test', lambda a, b: a+b)
        self.dispatcher.add_listener('test', lambda a, b: a+b)
        self.dispatcher.add_listener('test', lambda a, b: a+b)

        event_one = PEvent('test', EventType.Base,  max_responders=1)
        event_two = PEvent('test', EventType.Base, max_responders=2)
        event_max = PEvent('test', EventType.Base, max_responders=9999)
        event_neg = PEvent('test', EventType.Base, max_responders=-9999)

        self.assertEqual(1, len([listener for listener in self.dispatcher._get_listeners(event_one)]))
        self.assertEqual(2, len([listener for listener in self.dispatcher._get_listeners(event_two)]))
        self.assertEqual(3, len([listener for listener in self.dispatcher._get_listeners(event_max)]))
        self.assertEqual(3, len([listener for listener in self.dispatcher._get_listeners(event_neg)]))


if __name__ == '__main__':
    unittest.main()
