# PyTrigger

PyTrigger is a Python-based event-driven system that simplifies event management and handling within your applications. It provides a centralized hub for event registration, triggering, and asynchronous handling, enabling seamless communication between different components of your Python projects.

## Features

- **Event Listener Management:** Register and manage event listeners with different priorities.
- **Event Triggering:** Trigger events and notify registered listeners asynchronously.
- **Flexible Event Handling:** Handle various event types and associated data.
- **Priority-based Execution:** Execute listeners based on their assigned priority levels.
- **Scalability and Customization:** Scalable for different application scales and highly customizable.

## Basic Example

```python
from pytrigger import EventDispatcher, Event, EventType, Priority

# Create an instance of the EventDispatcher
dispatcher = EventDispatcher()

# Define an event called "example_event" of type USER_ACTION
my_event = Event(event_name="example_event", event_type=EventType.USER_ACTION)


# Define a listener function to handle the event
def on_event_triggered(event):
    # Print a message when the event is triggered
    print(f"Event '{event.event_name}' was triggered!")


# Register the listener function for the "example_event" event with normal priority
dispatcher.add_listener("example_event", on_event_triggered, priority=Priority.NORMAL)

# Trigger the "example_event" by dispatching the event through the EventDispatcher
dispatcher.sync_trigger(my_event)
```

## Advanced Usage
PyTrigger supports different event types, async event triggering, and more complex event management scenarios. Refer to the documentation (coming soon) for detailed usage and examples.

Contributing
Contributions are welcome! Feel free to raise issues, submit pull requests, or suggest enhancements. Please read our Contribution Guidelines for details.

License
This project is licensed under the MIT License.
