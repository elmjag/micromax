#!/usr/bin/env python3
import time
from PyTango import ConnectionFailed
from tango import Database, DbDevInfo
from tango.server import Device, attribute


TANGO_CONNECT_RETRY_TIME = 2.1
DEVICE_NAME = "g/ctl/machinestatus"


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
    db_info._class = "Billboard"
    db_info.server = "Billboard/0"
    db_info.name = DEVICE_NAME

    db.add_device(db_info)


class Billboard(Device):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @attribute(name="OperatorMessage", dtype=str)
    def operator_message(self):
        return "never send a human to do a machine's job"

    @attribute(name="R3NextInjection", dtype=str)
    def r3_next_injection(self):
        return "2024-06-12 14:00:00"

    @attribute(name="MachineMessage", dtype=str)
    def machine_message(self):
        return "<b>R3:</b> Shutdown<br><b>R1:</b> Shutdown<br><b>Linac:</b> Shutdown"

    @attribute(name="R3TopUp", dtype=int)
    def r3_top_up(self):
        return -1

    @attribute(name="R3Mode", dtype=str)
    def r3_mode(self):
        return "Delivery: Top-Up"


if __name__ == "__main__":
    register_device()
    Billboard.run_server()
