from typing import Callable, Coroutine, Union
from enum import Enum


class Priority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1


class EventListener:
    def __init__(self, callback: Union[Callable, Coroutine], priority: Priority = Priority.NORMAL, allow_busy_trigger: bool = True):
        self.callback = callback
        self.priority = priority
        self.allow_busy_trigger = allow_busy_trigger

    def __eq__(self, other: 'EventListener') -> bool:
        if not isinstance(other, EventListener):
            return False
        return self.priority == other.priority

    def __lt__(self, other: 'EventListener') -> bool:
        if not isinstance(other, EventListener):
            return False
        return self.priority.value < other.priority.value

    def __hash__(self) -> int:
        # We can use the hash value of the priority enum directly
        return hash(self.priority)
