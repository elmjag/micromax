import time
from tango import Database
from PyTango import ConnectionFailed


TANGO_CONNECT_RETRY_TIME = 0.6


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


def wait_for_tango(*_, **__):
    _connect_to_db()
    return True
