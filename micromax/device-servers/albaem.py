#!/usr/bin/env python

from tango.server import Device, attribute


class AlbaEm(Device):
    @attribute(name="InstantCurrent", dtype=float)
    def InstantCurrent(self):
        return 4.63615811718e-11


if __name__ == "__main__":
    AlbaEm.run_server()
