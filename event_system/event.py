from typing import Any, Callable, Union, Coroutine
from dataclasses import dataclass

from .event_type import EventType


@dataclass
class Event:
    event_name: str
    event_type: EventType
    data: Any = None
    source: Callable = None
    on_finish: Union[Callable, Coroutine] = None
    max_responders: int = -1
    allow_busy_trigger: bool = False
