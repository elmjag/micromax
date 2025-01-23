#!/usr/bin/env python3
import time
from PyTango import ConnectionFailed
from tango import Database, DbDevInfo
from tango.server import Device, attribute


TANGO_CONNECT_RETRY_TIME = 2.1
DEVICE_NAME = "r3-311l/id/idivu-01_gap"


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
    db_info._class = "Pool"
    db_info.server = "Pool/R3-311L"
    db_info.name = DEVICE_NAME

    db.add_device(db_info)


class Pool(Device):
    @attribute(name="Position", dtype=float)
    def _position(self):
        return 6.244225


if __name__ == "__main__":
    register_device()
    Pool.run_server()
