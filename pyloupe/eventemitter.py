class EventEmitter:
    def __init__(self):
        self._listeners = {}

    def on(self, event, callback):
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event, callback):
        """Remove a specific callback for an event."""
        if event in self._listeners:
            if callback in self._listeners[event]:
                self._listeners[event].remove(callback)
            if not self._listeners[event]:
                del self._listeners[event]

    def removeAllListeners(self, event=None):
        """Remove all callbacks for a specific event, or all events if no event is specified."""
        if event is not None:
            if event in self._listeners:
                del self._listeners[event]
        else:
            self._listeners = {}

    def emit(self, event, *args, **kwargs):
        for cb in list(self._listeners.get(event, [])):
            cb(*args, **kwargs)
