#!/usr/bin/env python
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
import re


class PathFixer(Device):
    Raw_path_readonly = device_property(dtype=bool, default_value=False)

    # attributes
    Proposals = attribute(dtype=[str], access=AttrWriteType.READ, max_dim_x=1000)
    Path = attribute(dtype=str, access=AttrWriteType.READ_WRITE)
    Type = attribute(dtype=str)
    UserName = attribute(
        dtype=str, access=AttrWriteType.READ_WRITE, memorized=True, hw_memorized=True
    )

    Proposal = attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        fisallowed="is_write_allowed",
    )

    Visits = attribute(dtype=[str], access=AttrWriteType.READ, max_dim_x=1000)
    Visit = attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        fisallowed="is_write_allowed",
    )

    Samples = attribute(dtype=[str], access=AttrWriteType.READ, max_dim_x=1000)
    Sample = attribute(
        dtype=str,
        access=AttrWriteType.READ_WRITE,
        memorized=True,
        hw_memorized=True,
        fisallowed="is_write_allowed",
    )

    SamplePath = attribute(dtype=str)

    ConfiguredDevices = attribute(dtype=[str], max_dim_x=1000)
    BadDevices = attribute(dtype=[str], max_dim_x=1000)
    Endstation = attribute(
        dtype=str, access=AttrWriteType.READ_WRITE, memorized=True, hw_memorized=True
    )

    RawPathReadonly = attribute(dtype=bool, access=AttrWriteType.READ)

    def read_RawPathReadonly(self):
        return self.Raw_path_readonly

    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.STANDBY)
        self.__path = "/tmp"
        self.__proposal = "12345"
        self.__username = "dapvan"
        self.__visit = "test"
        self.__sample = ""

    def read_Path(self):
        return self.__path

    def write_Path(self, path):
        self.__path = path

    def read_Proposal(self):
        return self.__proposal

    def write_Proposal(self, proposal):
        self.__proposal = proposal

    def read_Proposals(self):
        return [self.__proposal]

    def read_Type(self):
        return "Type"

    def read_UserName(self):
        return self.__username

    def write_UserName(self, username):
        self.__username = username

    def read_Visits(self):
        return ["test", "test2"]

    def read_Visit(self):
        return self.__visit

    def write_Visit(self, visit):
        self.__visit = visit

    def read_Samples(self):
        return []

    def read_Sample(self):
        return self.__sample

    def write_Sample(self, sample):
        pattern = re.compile("^[a-zA-Z0-9/]+$")
        if not pattern.match(sample):
            raise Exception(
                "Cannot set sample, please only use letters, numbers and '/'."
            )
        self.__sample = sample

    def read_SamplePath(self):
        return "path"

    def read_ConfiguredDevices(self):
        return ""

    def read_BadDevices(self):
        return ""

    def read_Endstation(self):
        return ""

    def write_Endstation(self, endstation):
        pass

    @command
    def TurnOn(self):
        # turn on the actual power supply here
        self.set_state(DevState.ON)

    @command
    def TurnOff(self):
        # turn off the actual power supply here
        self.set_state(DevState.OFF)


if __name__ == "__main__":
    PathFixer.run_server()
