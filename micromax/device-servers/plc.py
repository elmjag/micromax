#!/usr/bin/env python
import time

from tango import AttrWriteType
from tango.server import Device, attribute

ATTRIBUTES = [
    # Eiger detector cover tags
    "B312A_E06_DIA_DETC01_ENAC",
    "B312A_E06_DIA_DETC01_OPC",
    "B312A_E06_DIA_DETC01_CLC",
    # Jungfrau detector cover tags
    "B312A_E06_DIA_DETC02_ENAC",
    "B312A_E06_DIA_DETC02_OPC",
    "B312A_E06_DIA_DETC02_CLC",
]


class _DetectorCover:
    TRAVEL_TIME = 3.2  # in seconds

    def __init__(self):
        self._open = False
        self._toggle_state_at = None

    def _toggle_state(self):
        self._toggle_state_at = time.monotonic() + self.TRAVEL_TIME

    def is_open(self):
        def update_state():
            if self._toggle_state_at is None:
                # no update pending
                return

            if time.monotonic() < self._toggle_state_at:
                # too early to update the state
                return

            # it is time to toggle
            self._toggle_state_at = None
            self._open = not self._open

        update_state()
        return self._open

    def is_closed(self):
        return not self.is_open()

    def open(self):
        if self.is_open():
            # already open, nop
            return

        # start opening cover
        self._toggle_state()

    def close(self):
        if not self.is_open():
            # already closed, nop
            return

        # start closing cover
        self._toggle_state()


class VacPlc01(Device):
    """
    emulate (small subset) of b312a/vac/plc-01 device
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #
        # add some EIGER detector cover tags
        #
        eiger_cover = _DetectorCover()
        self._make_cls_attr(1, eiger_cover)
        self._make_ops_attr(1, eiger_cover)
        self._make_opc_attr(1, eiger_cover)
        self._make_clc_attr(1, eiger_cover)

        #
        # add some JUNGFRAU detector cover tags
        #
        jungfrau_cover = _DetectorCover()
        self._make_cls_attr(2, jungfrau_cover)
        self._make_ops_attr(2, jungfrau_cover)
        self._make_opc_attr(2, jungfrau_cover)
        self._make_clc_attr(2, jungfrau_cover)

    def _make_cls_attr(self, cover_number, cover: _DetectorCover):
        attr = attribute(name=f"B312A_E06_DIA_DETC0{cover_number}_CLS", dtype=bool)
        self.add_attribute(attr, lambda _, __: cover.is_closed())

    def _make_ops_attr(self, cover_number, cover: _DetectorCover):
        attr = attribute(name=f"B312A_E06_DIA_DETC0{cover_number}_OPS", dtype=bool)
        self.add_attribute(attr, lambda _, __: cover.is_open())

    def _make_opc_attr(self, cover_number, cover: _DetectorCover):
        def handle_write(*_):
            cover.open()

        attr = attribute(
            name=f"B312A_E06_DIA_DETC0{cover_number}_OPC",
            dtype=bool,
            access=AttrWriteType.READ_WRITE,
        )
        self.add_attribute(attr, lambda _, __: True, handle_write)

    def _make_clc_attr(self, cover_number, cover: _DetectorCover):
        def handle_write(*_):
            cover.close()

        attr = attribute(
            name=f"B312A_E06_DIA_DETC0{cover_number}_CLC",
            dtype=bool,
            access=AttrWriteType.READ_WRITE,
        )
        self.add_attribute(attr, lambda _, __: True, handle_write)


if __name__ == "__main__":
    VacPlc01.run_server()
