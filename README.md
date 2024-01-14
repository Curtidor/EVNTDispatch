# PyTrigger

PyTrigger is a Python-based event-driven system that simplifies event management and handling within your applications. It provides a centralized hub for event registration, triggering, and asynchronous handling, enabling seamless communication between different components of your Python projects.

## Features

- **Event Listener Management:** Register and manage event listeners with different priorities.
- **Event Triggering:** Trigger events and notify registered listeners asynchronously.
- **Flexible Event Handling:** Handle various event types and associated data.
- **Priority-based Execution:** Execute listeners based on their assigned priority levels.
- **Scalability and Customization:** Scalable for different application scales and highly customizable.

## Basic Async Example

```python
import asyncio

from event_system.event_dispatcher import EventDispatcher, PEvent, EventType

dispatcher = EventDispatcher()


async def process_message(event: PEvent):
    message_data, user_id = event.data
    # Simulate processing the message, e.g., storing it in a database or applying business logic
    print(f"Processing Message from User {user_id}: {message_data}")
    await asyncio.sleep(1)
    print("Message Processed")


async def send_message(user_id: int, message: str):
    await dispatcher.async_trigger(PEvent("new_message", EventType.Base, data=(message, user_id)))


async def main():
    dispatcher.start()

    dispatcher.add_listener("new_message", process_message)

    # Simulate users sending messages
    task = [send_message(1, "Hello, how are you?"),
            send_message(2, "I'm doing well, thanks!"),
            send_message(1, "What's new?"),
            send_message(3, "Not much, just relaxing.")
            ]
    await asyncio.gather(*task)

    await dispatcher.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage
PyTrigger supports different event types, async event triggering, and more complex event management scenarios. Refer to the documentation (coming soon) for detailed usage and examples.

Contributing
Contributions are welcome! Feel free to raise issues, submit pull requests, or suggest enhancements. Please read our Contribution Guidelines for details.

License
This project is licensed under the MIT License.
