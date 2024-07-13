from typing import Callable, Coroutine, Union
from enum import Enum

from .event_type import EventType


class Priority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1


class EventListener:
    def __init__(
            self, callback: Union[Callable, Coroutine], priority: Priority = Priority.NORMAL,
            allow_busy_trigger: bool = True, event_type: EventType = EventType.Base
    ):
        self.callback = callback
        self.priority = priority
        self.allow_busy_trigger = allow_busy_trigger
        self.event_type = event_type

    def __eq__(self, other: 'EventListener') -> bool:
        if not isinstance(other, EventListener):
            return False
        return (self.priority == other.priority and
                self.callback == other.callback and
                self.allow_busy_trigger == other.allow_busy_trigger and
                self.event_type == other.event_type)

    def __lt__(self, other: 'EventListener') -> bool:
        if not isinstance(other, EventListener):
            return False
        return self.priority.value < other.priority.value

    def __hash__(self) -> int:
        return hash((self.priority, self.callback, self.event_type))
