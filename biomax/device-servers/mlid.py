#!/usr/bin/env python
from tango.server import Device, attribute


#
# A dummy MovableLid emulated device.
#
# Currently, it's unclear which attributes and/or commands MXCuBE
# want to access. We only know it requires one device of this
# type to be present.
#
# For now this device only have one 'dummy' attribute, to be replaced
# in the future with other attributes and/or commands, when we learn
# was is actually needed to be emulated.
#


class MovableLid(Device):
    @attribute(name="Dummy", dtype=int)
    def _dummy(self):
        return 42


if __name__ == "__main__":
    MovableLid.run_server()
