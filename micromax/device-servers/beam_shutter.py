#!/usr/bin/env python
import time
from enum import Enum
from tango import DevState
from tango.server import Device, attribute, command


class Position(Enum):
    OPEN = 0
    CLOSED = 1


class Shutter:
    TRAVEL_TIME = 2.067

    def __init__(self):
        self._current_position = Position.OPEN
        self._destination_position = None
        self._arrival_time = None

    def _move_to_position(self, position):
        self._current_position = None
        self._destination_position = position
        self._arrival_time = time.monotonic() + self.TRAVEL_TIME

    def _update_position(self):
        if self._destination_position is None:
            # not moving, nothing to update
            return

        if time.monotonic() < self._arrival_time:
            # still moving, nothing to update
            return

        # we have arrived
        self._current_position = self._destination_position
        self._destination_position = None

    def open(self):
        if self._current_position == Position.OPEN:
            # already open, nothing to do
            return

        self._move_to_position(Position.OPEN)

    def close(self):
        if self._current_position == Position.CLOSED:
            # already closed, nothing to do
            return

        self._move_to_position(Position.CLOSED)

    def get_position(self):
        self._update_position()
        return self._current_position


class BeamShutter(Device):
    POS_TO_STATE = {
        Position.OPEN: DevState.OPEN,
        Position.CLOSED: DevState.CLOSE,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shutter = Shutter()

    def dev_state(self) -> DevState:
        pos = self._shutter.get_position()
        if pos is None:
            return DevState.MOVING

        return self.POS_TO_STATE[pos]

    @command
    def Open(self):
        self._shutter.open()

    @command
    def Close(self):
        self._shutter.close()


if __name__ == "__main__":
    BeamShutter.run_server()
