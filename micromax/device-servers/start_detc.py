#!/usr/bin/env python
"""
A custom script to start MXDetectorCover tango device server.

This script waits until the PLC device is pingable and _then_ starts the
MXDetectorCover tango ds. This is needed because MXDetectorCover fails to
start properly if PLC device have not yet started.

Yes, there are probably better ways to deal with these start-up dependencies.
"""
import sys
import time
import subprocess
from tango import DeviceProxy
from PyTango import DevFailed


PLC_DEVICE = "b312a/vac/plc-01"
RETRY_TIME = 0.1


def parse_args():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <instance-name>")
        sys.exit(1)

    return sys.argv[1]


def wait_for_plc():
    plc_dev = DeviceProxy(PLC_DEVICE)

    while True:
        try:
            plc_dev.ping()
            return True
        except DevFailed:
            print(f"failed to ping {PLC_DEVICE}, retrying in {RETRY_TIME} seconds")
            time.sleep(RETRY_TIME)


def main():
    instance = parse_args()
    wait_for_plc()
    subprocess.run(["/opt/conda/bin/MXDetectorCover", instance])


main()
