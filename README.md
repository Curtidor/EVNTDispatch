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

# Initialize the Event Dispatcher
dispatcher = EventDispatcher()

# Define an event
my_event = Event(event_name="example_event", event_type=EventType.USER_ACTION)

# Define a listener function
def on_event_triggered(event):
    print(f"Event '{event.event_name}' was triggered!")

# Register the listener
dispatcher.add_listener("example_event", on_event_triggered, priority=Priority.NORMAL)

# Trigger the event
dispatcher.trigger(my_event)
```

## Advanced Usage
PyTrigger supports different event types, async event triggering, and more complex event management scenarios. Refer to the documentation (coming soon) for detailed usage and examples.

Contributing
Contributions are welcome! Feel free to raise issues, submit pull requests, or suggest enhancements. Please read our Contribution Guidelines for details.

License
This project is licensed under the MIT License.
