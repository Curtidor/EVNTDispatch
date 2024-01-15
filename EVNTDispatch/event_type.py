from enum import Enum


class EventType(Enum):
    Base = 0
    UserInteraction = 1
    SystemEvent = 2
    NetworkEvent = 3
    FileEvent = 4
    TimerEvent = 5
    ErrorEvent = 6
    LogEvent = 7
    # ... add more event types as needed
