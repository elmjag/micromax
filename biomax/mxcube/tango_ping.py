import time
from tango import Database, DeviceProxy
from PyTango import ConnectionFailed, DevFailed


TANGO_CONNECT_RETRY_TIME = 0.6

SARDANA_DS = "dserver/sardana/biomax"


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


def _ping_sardana_ds():
    while True:
        try:
            DeviceProxy(SARDANA_DS).ping()
            return
        except DevFailed:
            print(
                f"failed to connect to {SARDANA_DS}, retrying in {TANGO_CONNECT_RETRY_TIME} seconds"
            )
            time.sleep(TANGO_CONNECT_RETRY_TIME)


def wait_for_tango(*_, **__):
    _connect_to_db()
    _ping_sardana_ds()
    return True
