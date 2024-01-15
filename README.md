# EVNTDispatch

EVNTDispatch is a versatile Python library designed to facilitate event-driven programming by providing a flexible event dispatcher. Whether you are building a graphical user interface, a command-line application, or a complex system with asynchronous components, the Event System simplifies communication and coordination between different parts of your code.

## Key Features
* **Event Dispatching:** Easily define and dispatch events to notify components of changes or user interactions.

* **Asynchronous Support:** Seamlessly integrate asynchronous event listeners for efficient handling of time-consuming tasks without blocking the main execution.

* **Priority and Max Responders:** Control the order of event listener execution and limit the number of responders for fine-grained control over event handling.
 
* **Task Scheduling:** Schedule tasks to be executed after a specified delay, adding a layer of automation to your application.
## Basic Async Example

```python
import asyncio

from EVNTDispatch import EventDispatcher, PEvent, EventType

dispatcher = EventDispatcher()

# All event listeners must have a single parameter of type PEvent
async def process_message(event: PEvent):
    message_data, user_id = event.data
    
    # Simulate processing the message, e.g., storing it in a database or applying business logic
    print(f"Processing Message from User {user_id}: {message_data}")
    await asyncio.sleep(1)
    
    print("Message Processed")

async def send_message(user_id: int, message: str):
    # Trigger an event called 'new_message', notifying any listeners subscribed to 'new_message'
    await dispatcher.async_trigger(PEvent("new_message", EventType.Base, data=(message, user_id)))

async def main():
    # Start the event dispatcher
    dispatcher.start()
    
    # Subscribe 'process_message' to events called 'new_message'
    dispatcher.add_listener("new_message", process_message)

    # Tasks to simulate users sending messages
    tasks = [
        send_message(1, "Hello, how are you?"),
        send_message(2, "I'm doing well, thanks!"),
        send_message(1, "What's new?"),
        send_message(3, "Not much, just relaxing.")
    ]
    
    # Execute tasks concurrently
    await asyncio.gather(*tasks)
    
    # Close the dispatcher to wait for all tasks to finish
    await dispatcher.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### License
This project is licensed under the MIT License.
