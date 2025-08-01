#!/usr/bin/env python
from random import random
from tango.server import Device, attribute

#
# A BeamlineXbpm emulated device.
#
# Currently, it's unclear which attributes and/or commands MXCuBE
# want to access except 'S' for the CheckBeam purpose.
# It may be filled with other attributes and/or commands in the future.
#


class BeamlineXbpm(Device):

    @attribute(name="S", dtype=float)
    def _s(self):
        return (random() + 1) / 1e-7


if __name__ == "__main__":
    BeamlineXbpm.run_server()
