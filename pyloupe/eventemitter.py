from typing import Any, Callable, Dict, List, Optional, Union


class EventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable) -> None:
        """Add a callback for an event.

        Args:
            event: The event name to listen for
            callback: The function to call when the event is emitted
        """
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable) -> None:
        """Remove a specific callback for an event.

        Args:
            event: The event name
            callback: The callback function to remove
        """
        if event in self._listeners:
            if callback in self._listeners[event]:
                self._listeners[event].remove(callback)
            if not self._listeners[event]:
                del self._listeners[event]

    def removeAllListeners(self, event: Optional[str] = None) -> None:
        """Remove all callbacks for a specific event, or all events if no event is specified.

        Args:
            event: The event name to remove listeners for, or None to remove all listeners
        """
        if event is not None:
            if event in self._listeners:
                del self._listeners[event]
        else:
            self._listeners = {}

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event with arguments.

        Args:
            event: The event name to emit
            *args: Positional arguments to pass to the callbacks
            **kwargs: Keyword arguments to pass to the callbacks
        """
        for cb in list(self._listeners.get(event, [])):
            cb(*args, **kwargs)
