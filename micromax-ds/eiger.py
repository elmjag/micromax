#!/usr/bin/env python
import time
from typing import Optional, Union, Any
from dataclasses import dataclass
from threading import Thread
from tango import AttrWriteType, DevLong
from tango.server import Device, attribute, command


SOFTWARE_TRIGGERED_COLLECTION_LENGTH = 12.0


def delayed(delay, delayed_call):
    def run():
        time.sleep(delay)
        delayed_call()

    Thread(target=run).start()


@dataclass
class _WriteableAttr:
    name: str
    dtype: type
    default_value: Any
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None


WRITEABLE_ATTRIBUTES = [
    _WriteableAttr("DiscardNew", bool, False),
    _WriteableAttr("MonitorMode", str, "enabled"),
    _WriteableAttr("FilewriterMode", str, "enabled"),
    _WriteableAttr("PhotonEnergy", float, 6000, min_value=4000, max_value=160000),
    _WriteableAttr("Compression", str, "bslz4"),
    _WriteableAttr("CountTime", float, 32.2),
    _WriteableAttr("FrameTime", float, 0.04, min_value=0.00204081693664193),
    _WriteableAttr("OmegaStart", float, 1.1),
    _WriteableAttr("BeamCenterX", float, 1465.8004),
    _WriteableAttr("BeamCenterY", float, 1920.6501),
    _WriteableAttr("DetectorDistance", float, 0.50000834),
    _WriteableAttr("FilenamePattern", str, "/tmp/data"),
    _WriteableAttr("ImagesPerFile", int, 100),
    _WriteableAttr("NbImages", int, 1800),
    _WriteableAttr("NbTriggers", int, 29),
    _WriteableAttr("OmegaIncrement", float, 0.1),
    _WriteableAttr("RoiMode", str, "disabled"),
    _WriteableAttr("TriggerMode", str, "exts"),
    _WriteableAttr("HeaderAppendix", str, "{}"),
]


class Eiger(Device):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._attribute_vals = dict()
        self._status = "idle"
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

    def dev_status(self) -> str:
        return f"{self._status}\n\n"

    #
    # read-only attributes
    #

    @attribute(name="CountrateCorrectionCountCutoff", dtype=DevLong)
    def count_rate_correction_count_cutoff(self):
        return 83270

    @attribute(name="Temperature", dtype=float)
    def temperature(self):
        return 24.2

    @attribute(name="Humidity", dtype=float)
    def humidity(self):
        return 80.2

    @attribute(name="Wavelength", dtype=float)
    def wavelength(self):
        return 0.04

    @attribute(name="EnergyThreshold", dtype=float)
    def energy_threshold(self):
        return 5000

    @attribute(name="FlatfieldEnabled", dtype=bool)
    def flatfield_enabled(self):
        return False

    @attribute(name="AutoSummationEnabled", dtype=bool)
    def auto_summation_enabled(self):
        return False

    @attribute(name="RateCorrectionEnabled", dtype=bool)
    def rate_correction_enabled(self):
        return False

    @attribute(name="BitDepth", dtype=int)
    def bit_depth(self):
        return 16

    @attribute(name="ReadoutTime", dtype=float)
    def readout_time(self):
        return 0.23

    @attribute(name="Description", dtype=str)
    def description(self):
        return "Description TBD"

    @attribute(name="Time", dtype=str)
    def time(self):
        return "Time TBD"

    @attribute(name="XPixelSize", dtype=float)
    def x_pixel_size(self):
        return 0.23

    @attribute(name="YPixelSize", dtype=float)
    def y_pixel_size(self):
        return 0.23

    @attribute(name="CountTimeInte", dtype=float)
    def count_time_inte(self):
        return 0.23

    @attribute(name="DownloadDirectory", dtype=str)
    def download_directory(self):
        return "DownloadDirectory TBD"

    @attribute(name="FilesInBuffer", dtype=str)
    def files_in_buffer(self):
        return "FilesInBuffer TBD"

    @attribute(name="Error", dtype=str)
    def error(self):
        return "Error TBD"

    @attribute(name="XPixelsDetector", dtype=int)
    def x_pixels_detector(self):
        return 2 ** 16

    @attribute(name="YPixelsDetector", dtype=int)
    def y_pixels_detector(self):
        return 2 ** 16

    @attribute(name="CollectionUUID", dtype=str)
    def collection_uuid(self):
        return "f12336a0-dcbe-484d-9f86-2fc4ac614846"

    @attribute(name="HeaderDetail", dtype=str)
    def header_detail(self):
        return "HeaderDetail TBD"

    @attribute(name="ImageAppendix", dtype=str)
    def image_appendix(self):
        return "ImageAppendix TBD"

    @attribute(name="StreamState", dtype=str)
    def stream_state(self):
        return "StreamState TBD"

    # remaining buffer space in KB
    @attribute(name="BufferFree", dtype="DevULong64")
    def buffer_free(self):
        return 1024 * 1024 * 10

    # The filewriter`s status. The status can be one of disabled,
    # ready, acquire, and error.
    @attribute(name="FilewriterState", dtype=str)
    def filewriter_state(self):
        return "ready"

    # image_nr_low metadata parameter in the first HDF5 data file
    @attribute(name="ImageNbStart", dtype=int)
    def image_nb_start(self):
        return 0

    #
    # commands
    #

    @command
    def Cancel(self):
        self._status = "idle"

    @command
    def Arm(self):
        self._status = "ready"

    @command
    def Disarm(self):
        self._status = "idle"

    @command
    def EnableStream(self):
        pass

    @command
    def DisableStream(self):
        pass

    @command
    def Abort(self):
        self._status = "idle"

    @command
    def Trigger(self):
        if self._status != "ready":
            # detector is unarmed, can't be triggered
            raise Exception(
                "Detector in idle state, not 'ready',  try the arm command first"
            )

        self._status = "acquire"

        def datacollection_finished():
            if self._status == "acquire":
                # collection finished, unless it was aborted earlier
                self._status = "idle"

        delayed(SOFTWARE_TRIGGERED_COLLECTION_LENGTH, datacollection_finished)


if __name__ == "__main__":
    Eiger.run_server()
