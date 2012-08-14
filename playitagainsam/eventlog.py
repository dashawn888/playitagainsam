#  Copyright (c) 2012, Ryan Kelly.
#  All rights reserved; available under the terms of the MIT License.
"""

playitagainsam.eventlog:  event reader/writer for playitagainsam
================================================================

"""

import json


class EventLog(object):

    def __init__(self, datafile, mode):
        self.datafile = datafile
        self.mode = mode
        if mode == "r":
            with open(self.datafile, "r") as f:
                data = json.loads(f.read())
            self.events = data["events"]
            self._event_stream = None
        else:
            self.events = []

    def close(self):
        if self.mode != "r":
            with open(self.datafile, "w") as f:
                data = {"events": self.events}
                output = json.dumps(data, indent=2, sort_keys=True)
                f.write(output)

    def write_event(self, event):
        # Append an event to the event log.
        # We try to do some basic simplifications.
        # Collapse consecutive "PAUSE" events into a single pause.
        if event["act"] == "PAUSE":
            if self.events and self.events[-1]["act"] == "PAUSE":
                self.events[-1]["duration"] += event["duration"]
                return
        # Try to collapse consecutive IO events on the same terminal.
        if event["act"] == "WRITE" and self.events:
            if self.events[-1].get("term") == event["term"]:
                # Collapse consecutive writes into a single chunk.
                if self.events[-1]["act"] == "WRITE":
                    self.events[-1]["data"] += event["data"]
                    return
                # Collapse read/write of same data into an "ECHO".
                if self.events[-1]["act"] == "READ":
                    if self.events[-1]["data"] == event["data"]:
                        self.events[-1]["act"] = "ECHO"
                        # Collapse consecutive "ECHO" events.
                        if len(self.events) > 1:
                            if self.events[-2]["act"] == "ECHO":
                                if self.events[-2]["term"] == event["term"]:
                                    self.events[-2]["data"] += event["data"]
                                    del self.events[-1]
                        return
        # Otherwise, just add it to the list.
        self.events.append(event)

    def read_event(self):
        if self._event_stream is None:
            self._event_stream = self._iter_events()
        try:
            return self._event_stream.next()
        except StopIteration:
            return None

    def _iter_events(self):
        for event in self.events:
            if event["act"] == "ECHO":
                for c in event["data"]:
                    yield {"act": "READ", "term": event["term"], "data": c}
                    yield {"act": "WRITE", "term": event["term"], "data": c}
            elif event["act"] == "READ":
                for c in event["data"]:
                    yield {"act": "READ", "term": event["term"], "data": c}
            else:
                yield event
