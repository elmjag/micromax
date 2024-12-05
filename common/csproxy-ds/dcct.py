#!/usr/bin/env python3
import time
from itertools import cycle
from PyTango import ConnectionFailed
from tango import Database, DbDevInfo
from tango.server import Device, attribute

CURRENTS = [
    0.39518965682844615,
    0.395918248053309,
    0.39664013397652653,
    0.39762002574983546,
    0.3981098345249726,
    0.39859072410449725,
    0.39908062355605123,
    0.39979803818127974,
    0.3998840604847532,
]


TANGO_CONNECT_RETRY_TIME = 2.1
DEVICE_NAME = "r3-319s2/dia/dcct-01"


def _connect_to_db():
    db = None
    while db is None:
        try:
            db = Database()
        except ConnectionFailed:
            print(
                f"failed to connect to tango host, retrying in {TANGO_CONNECT_RETRY_TIME} seconds"
            )
            time.sleep(TANGO_CONNECT_RETRY_TIME)

    return db


def register_device():
    db = _connect_to_db()

    db_info = DbDevInfo()
    db_info._class = "Dcct"
    db_info.server = "Dcct/0"
    db_info.name = DEVICE_NAME

    db.add_device(db_info)


class Dcct(Device):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._currents = cycle(CURRENTS)

    @attribute(name="Current", dtype=float)
    def current(self):
        return next(self._currents)

    @attribute(name="Lifetime", dtype=float)
    def lifetime(self):
        return 33627.44279505807


if __name__ == "__main__":
    register_device()
    Dcct.run_server()
