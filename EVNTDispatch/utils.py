import inspect

from .event_listener import EventListener, EventType
from .pevent import PEvent


def does_event_type_match(listener: EventListener, event: PEvent) -> bool:
    """
    Check if the event type of listener matches the event's type.

    Parameters:
    - listener (EventListener): The event listener to check.
    - event (PEvent): The event to compare the type with.

    Returns:
    bool: True if the event types match or the event type is EventType.Base, False otherwise.
    """
    if event.event_type == EventType.Base or listener.event_type == event.event_type:
        return True

    return False


def count_parameters(func):
    signature = inspect.signature(func)

    num_params = len(signature.parameters)

    return num_params
