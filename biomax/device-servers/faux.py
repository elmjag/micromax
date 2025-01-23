from typing import Optional, Iterator
from dataclasses import dataclass
from sardana import State
from sardana.pool.controller import MotorController
from sardana.pool.controller import Type, Description


@dataclass
class _Motor:
    start_position: Optional[float] = None
    steps: Optional[Iterator[float]] = None
    position: Optional[float] = None
    # if not powered on, moving motor will throw 'not ready' error
    power_on: bool = True


class FauxMotorController(MotorController):
    axis_attributes = {
        "StartPosition": {
            Type: float,
            Description: "movable will start at this position, when Pool is initialized",
        },
        "powerOn": {
            Type: bool,
            Description: "is motor powered on",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._motors = {}

    def getpowerOn(self, axis):
        return self._motors[axis].power_on

    def setpowerOn(self, axis, value):
        self._motors[axis].power_on = value

    def getStartPosition(self, axis):
        return self._motors[axis].start_position

    def setStartPosition(self, axis, value):
        motor = self._motors[axis]

        motor.start_position = value

        if motor.position is None:
            motor.position = value

    def AddDevice(self, axis):
        self._motors[axis] = _Motor()

    def DeleteDevice(self, axis):
        del self._motor[axis]

    def StateOne(self, axis):
        motor = self._motors[axis]
        if not motor.power_on:
            return State.Off

        if motor.steps:
            return State.Moving

        return State.On

    def _move_motor(self, motor: _Motor):
        if motor.steps is None:
            # no move steps, nothing to do here
            return

        try:
            motor.position = next(motor.steps)
        except StopIteration:
            motor.steps = None

    def ReadOne(self, axis):
        motor = self._motors[axis]
        self._move_motor(motor)

        return motor.position

    def StartOne(self, axis, position):
        def steps(start, end, step_nums):
            step = (end - start) / step_nums
            for n in range(step_nums):
                yield start + step * n

            yield end

        motor = self._motors[axis]
        if not motor.power_on:
            raise RuntimeError(
                f"Error sending command, IcePAP answered MOVE ERROR Axis {axis}: Not Ready"
            )

        motor.steps = steps(motor.position, position, 20)
