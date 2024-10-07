#!/usr/bin/env python
import time
from enum import Enum
from typing import Optional, Union, Any
from dataclasses import dataclass
from threading import Thread
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command


ARM_DELAY = 1.2
DISARM_DELAY = 0.8
SOFTWARE_TRIGGERED_COLLECTION_LENGTH = 12.0


@dataclass
class _WriteableAttr:
    name: str
    dtype: type
    default_value: Any
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None


WRITEABLE_ATTRIBUTES = [
    _WriteableAttr("beam_x_pxl", float, 0.0),
    _WriteableAttr("beam_y_pxl", float, 0.0),
    _WriteableAttr("storage_cell_count", int, 15),
    _WriteableAttr("file_prefix", str, ""),
    _WriteableAttr("goniometer__name", str, ""),
    _WriteableAttr("goniometer__start", float, 0.0),
    _WriteableAttr("goniometer__step", float, 0.0),
    _WriteableAttr("goniometer__vector__#1", float, 0.0),
    _WriteableAttr("goniometer__vector__#2", float, 0.0),
    _WriteableAttr("goniometer__vector__#3", float, 0.0),
    _WriteableAttr("detector_distance_mm", float, 0),
    _WriteableAttr("image_time_us", int, 0),
    _WriteableAttr("images_per_file", int, 0),
    _WriteableAttr("images_per_trigger", int, 0),
    _WriteableAttr("incident_energy_keV", float, 0),
    _WriteableAttr("ntrigger", int, 0),
    _WriteableAttr("frame_time_us", int, 500),
    _WriteableAttr("summation", int, 5),
    _WriteableAttr("unit_cell__a", float, 0.0),
    _WriteableAttr("unit_cell__b", float, 0.0),
    _WriteableAttr("unit_cell__c", float, 0.0),
    _WriteableAttr("unit_cell__alpha", float, 0.0),
    _WriteableAttr("unit_cell__beta", float, 0.0),
    _WriteableAttr("unit_cell__gamma", float, 0.0),
]


class _DetectorState(Enum):
    IDLE = 1  # unarmed
    MEASURING = 2  # armed and possibly taking pictures


DETECTOR_TO_TANGO_STATE = {
    _DetectorState.IDLE: DevState.ON,
    _DetectorState.MEASURING: DevState.RUNNING,
}


def delayed(delay, delayed_call):
    def run():
        time.sleep(delay)
        delayed_call()

    Thread(target=run).start()


class Jungfrau(Device):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._state = _DetectorState.IDLE

        self._attribute_vals = dict()
        self._init_writeable_attributes()

    def _init_writeable_attributes(self):
        def attr_reader(name):
            return self._attribute_vals[name]

        def attr_writer(name, value):
            self._attribute_vals[name] = value

        def make_reader(attr_name):
            return lambda _, __, name=attr_name: attr_reader(name)

        def make_writer(attr_name):
            return lambda _, attrib, name=attr_name: attr_writer(
                name, attrib.get_write_value()
            )

        for attr in WRITEABLE_ATTRIBUTES:
            attr_cfg = dict(
                name=attr.name, dtype=attr.dtype, access=AttrWriteType.READ_WRITE
            )
            if attr.min_value is not None:
                attr_cfg["min_value"] = attr.min_value

            if attr.max_value is not None:
                attr_cfg["max_value"] = attr.max_value

            self.add_attribute(
                attribute(**attr_cfg),
                make_reader(attr.name),
                make_writer(attr.name),
            )

            self._attribute_vals[attr.name] = attr.default_value

    def dev_state(self) -> DevState:
        return DETECTOR_TO_TANGO_STATE[self._state]

    @command
    def Arm(self):
        # emulate that it take a second or so to arm the detector
        time.sleep(ARM_DELAY)
        self._state = _DetectorState.MEASURING

    @command
    def SoftwareTrigger(self):
        if self._state != _DetectorState.MEASURING:
            raise Exception("detector needs to be in armed state")

        def datacollection_finished():
            self._state = _DetectorState.IDLE

        delayed(SOFTWARE_TRIGGERED_COLLECTION_LENGTH, datacollection_finished)

    @command
    def Stop(self):
        def set_armed_false():
            self._state = _DetectorState.IDLE

        if self._state != _DetectorState.MEASURING:
            # if not armed nor measuring, this is a NOP command
            return

        # emulate that it takes some time to dis-arm and stop the detector
        delayed(DISARM_DELAY, set_armed_false)

    @command
    def Pedestal(self):
        # NOP for now
        pass


if __name__ == "__main__":
    Jungfrau.run_server()
