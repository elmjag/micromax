#!/usr/bin/env python3
from typing import Optional, Any
from collections.abc import Callable
import asyncio
import sys
import math
import traceback
from time import time
from asyncio import StreamReader, StreamWriter, Lock
from datetime import datetime
from atcpserv import AsyncTCPServer
from dataclasses import dataclass, field

MOTOR_STEPS = 8
PORT = 9001

STX = b"\02"
ETX = b"\03"
ARRAY_SEP = "\x1f"

READ = "READ "
WRTE = "WRTE "
LIST = "LIST"
EXEC = "EXEC "
NAME = "NAME"

BEAMSTOP_TRAVEL_TIME_SEC = 2.6
# supported predefined beamstop positions
BEAMSTOP_POSITIONS = ["PARK", "BEAM", "TRANSFER", "OFF"]

PHASE_CHANGE_TIME_SEC = 3.1
# supported MD3 phases
PHASES = ["Centring", "BeamLocation", "DataCollection", "Transfer"]

# common attribute types
STATE = "org.embl.State"
DOUBLE = "java.lang.Double"
STRING = "java.lang.String"
INTEGER = "java.lang.Integer"
BOOLEAN = "java.lang.Boolean"

INITIAL_EVENTS = [
    "Omega",
    "AlignmentX",
    "AlignmentY",
    "AlignmentZ",
    "CentringX",
    "CentringY",
    "CapillaryVertical",
    "CapillaryHorizontal",
    "ApertureVertical",
    "ApertureHorizontal",
    "ScintillatorHorizontal",
    "ScintillatorVertical",
    "BeamstopX",
    "BeamstopY",
    "BeamstopZ",
    "Zoom",
]


@dataclass
class CoaxCamScale:
    x: float
    y: float


COAX_CAM_SCALES = [
    # zoom level 1
    CoaxCamScale(x=0.0018851562499999997, y=0.0018851562499999997),
    # zoom level 2
    CoaxCamScale(x=0.0015743281249999996, y=0.0015743281249999996),
    # zoom level 3
    CoaxCamScale(x=0.0012289635416666664, y=0.0012289635416666664),
    # zoom level 4
    CoaxCamScale(x=0.000950012567708333, y=0.000950012567708333),
    # zoom level 5
    CoaxCamScale(x=0.00023299124062499998, y=0.00023299124062499998),
    # zoom level 6
    CoaxCamScale(x=0.00018080156250000008, y=0.00018080156250000008),
    # zoom level 7
    CoaxCamScale(x=0.00011700000000000001, y=0.00011700000000000001),
]



@dataclass
class Attribute:
    _val: Any
    type: str
    # This callback function is meant to provide a way to validate and/or modify the new value before it's set.
    value_transform: Callable[[Any], Any] = field(default=lambda val: val) #identity function by default


    @property
    def val(self):
        return self._val
    
    @val.setter
    def val(self, val: Any):
        self._val = self.value_transform(val)

@dataclass
class Task:
    name: str
    # times are in unix epoch seconds
    start_time: float
    end_time: float

    def is_running(self) -> bool:
        return self.end_time > time()


AttributeUpdatedCallback = Callable[[str, Attribute, int], None]


class UnknownAttribute(Exception):
    pass


class UnknownCommand(Exception):
    pass


class CommandError(Exception):
    pass


class DisallowedState(Exception):
    """Exception for cases where a command or attribute is invoked, although it is not allowed in the current state."""


def log(msg: str):
    print(msg)
    sys.stdout.flush()


def encode_val(val) -> str:
    def encode_list():
        str_lst = [encode_val(v) for v in val]
        return ARRAY_SEP + ARRAY_SEP.join(str_lst) + ARRAY_SEP

    def encode_float():
        if math.isinf(val):
            txt = "Infinity"
            if val < 0:
                txt = "-" + txt
            return txt

        return str(val)

    val_type = type(val)

    if val_type == str:
        return val

    if val_type == int:
        return str(val)

    if val_type == float:
        return encode_float()

    if val_type in (list, tuple):
        return encode_list()

    if val_type == bool:
        return "true" if val else "false"

    if val_type == type(None):
        return "null"

    assert False, f"unsupported value type {val_type}"


def parse_val(val_type, val):
    def parse_bool(val: str) -> bool:
        val = val.lower()
        if val == "true":
            return True
        if val == "false":
            return False

        assert False, f"unexpected boolean {val}"

    if val_type == int:
        return int(val)

    if val_type == bool:
        return parse_bool(val)

    if val_type == float:
        return float(val)

    if val_type == str:
        return val

    assert False, f"unsupported value type {val_type}"


def epoch_as_text(epoch: float) -> str:
    """
    convert time in epoch seconds to textual date-time format
    """
    txt = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S.%f")
    # cut of last 3 digit, so that seconds are returned with milliseconds precision,
    # e.g '2023-12-12 15:44:15.695130' becomes '2023-12-12 15:44:15.695'
    return txt[:-3]


class SynchronizedWriter:
    def __init__(self, writer: StreamWriter):
        self._writer = writer
        self._lock = Lock()

    async def write_drain(self, msg):
        async with self._lock:
            self._writer.write(msg)
            await self._writer.drain()


class MD3Up:
    def __init__(self):
        self._attr_updated_callbacks: set[AttributeUpdatedCallback] = set()
        self._synchronization_id = 0
        self._tasks = {}

        self._motors = {
            # name: (limits)
            "AlignmentX": (-5.6, 6.1),
            "AlignmentY": (-77.0, 2.0),
            "AlignmentZ": (-3.399, 6.1),
            "Omega": (-math.inf, math.inf),
            "CentringX": (-3.05, 3.05),
            "CentringY": (-3.05, 3.5),
            "CentringTableFocus": (-3.19668, 3.19871),
        }

        self._attrs = {
            # note: the AlignmentTablePosition type signature is a guess
            "AlignmentTablePosition": Attribute(
                "TRANSFER", "org.embl.md.dev.AlignmentTable$Position"
            ),
            "AlignmentXPosition": Attribute(6.582e-06, DOUBLE),
            "AlignmentXState": Attribute("Ready", STATE),
            "AlignmentYPosition": Attribute(9.362e-06, DOUBLE),
            "AlignmentYState": Attribute("Ready", STATE),
            "AlignmentZPosition": Attribute(5.712e-05, DOUBLE),
            "AlignmentZState": Attribute("Ready", STATE),
            "ApertureDiameters": Attribute([5, 10, 15, 20, 50, 600], "TODO"),
            "ApertureHorizontalPosition": Attribute(0.3077, DOUBLE),
            "ApertureHorizontalState": Attribute("Ready", STATE),
            # note: the AperturePosition type signature is a guess
            "AperturePosition": Attribute("BEAM", "org.embl.md.dev.Aperture$Position"),
            "ApertureVerticalPosition": Attribute(-4.778, DOUBLE),
            "ApertureVerticalState": Attribute("Ready", STATE),
            "BackLightFactor": Attribute(1.6, DOUBLE),
            "BackLightIsOn": Attribute(False, BOOLEAN),
            "BeamstopDistancePosition": Attribute(6.863187356482003, DOUBLE),
            # note: the BeamstopPosition type signature is a guess
            "BeamstopPosition": Attribute("PARK", "org.embl.md.dev.Beamstop$Position", self._move_beamstop_check),
            "BeamstopXPosition": Attribute(6.93, DOUBLE),
            "BeamstopXState": Attribute("Ready", STATE),
            "BeamstopYPosition": Attribute(4.75, DOUBLE),
            "BeamstopYState": Attribute("Ready", STATE),
            "BeamstopZPosition": Attribute(-94.3, DOUBLE),
            "BeamstopZState": Attribute("Ready", STATE),
            "CameraExposure": Attribute(40000.0, DOUBLE),
            "CapillaryHorizontalPosition": Attribute(-2.1114864865e-6, DOUBLE),
            "CapillaryHorizontalState": Attribute("Ready", STATE),
            # note: the CapillaryPosition type signature is a guess
            "CapillaryPosition": Attribute(
                "PARK", "org.embl.md.dev.Capillary$Position"
            ),
            "CentringTableFocusPosition": Attribute(0.42, DOUBLE),
            "CentringTableFocusState": Attribute("Ready", STATE),
            "CapillaryVerticalPosition": Attribute(-93.49539792171772, DOUBLE),
            "CapillaryVerticalState": Attribute("Ready", STATE),
            "CentringTableVerticalPosition": Attribute(-1.174697170195887e-05, DOUBLE),
            "CentringXPosition": Attribute(1.746e-06, DOUBLE),
            "CentringXState": Attribute("Ready", STATE),
            "CentringYPosition": Attribute(1.174e-05, DOUBLE),
            "CentringYState": Attribute("Ready", STATE),
            "CoaxCamScaleX": Attribute(0.0018851562499999997, DOUBLE),
            "CoaxCamScaleY": Attribute(0.0018851562499999997, DOUBLE),
            "CoaxialCameraZoomValue": Attribute(1, INTEGER),
            "CurrentApertureDiameterIndex": Attribute(2, INTEGER),
            "CurrentPhase": Attribute(
                "Transfer",
                "org.embl.md.RemoteInterface$Phase",
            ),
            "DetectorDistance": Attribute(700.0, DOUBLE),
            "DetectorState": Attribute("Ready", STATE),
            "DirectBeamEnabled": Attribute(False, BOOLEAN),
            "FastShutterIsOpen": Attribute(False, BOOLEAN, self._fast_shutter_direct_beam_check),
            "FrontLightFactor": Attribute(0.9, DOUBLE),
            "FrontLightIsOn": Attribute(False, BOOLEAN),
            # note: the HeadType type signature is a guess
            "HeadType": Attribute(
                "SmartMagnet", "org.embl.md.RemoteInterface$HeadType"
            ),
            "LastTaskInfo": Attribute(
                [
                    "Hot Start",
                    "0",
                    "2023-08-04 10:41:57.125",
                    "2023-08-04 10:41:57.325",
                    "true",
                    "null",
                    "1",
                ],
                "TODO",
            ),
            "OmegaPosition": Attribute(359.999979169585, DOUBLE),
            "OmegaState": Attribute("Ready", STATE),
            "PlateLocation": Attribute("null", "TODO"),
            "SampleHolderLength": Attribute(22.0, DOUBLE),
            "SampleIsLoaded": Attribute(False, BOOLEAN),
            "ScanExposureTime": Attribute(0.663, DOUBLE),
            "ScanNumberOfFrames": Attribute(1, INTEGER),
            "ScanRange": Attribute(6.0, DOUBLE),
            "ScanStartAngle": Attribute(246.798, DOUBLE),
            "ScintillatorHorizontalPosition": Attribute(-89.99992208163434, DOUBLE),
            "ScintillatorHorizontalState": Attribute("Ready", STATE),
            # note: the ScintillatorPosition type signature is a guess
            "ScintillatorPosition": Attribute(
                "UNKNOWN", "org.embl.md.dev.Scintillator$Position"
            ),
            "ScintillatorVerticalPosition": Attribute(-89.99992208163434, DOUBLE),
            "ScintillatorVerticalState": Attribute("Ready", STATE),
            "State": Attribute("Ready", STATE),
            "Status": Attribute("Ready", STRING),
            # note: the TransferMode type signature is a guess
            "TransferMode": Attribute(
                "SAMPLE_CHANGER", "org.embl.md.RemoteInterface$TransferMode"
            ),
            "ZoomPosition": Attribute(0.0, DOUBLE),
            "ZoomState": Attribute("Ready", STATE),
        }

        self._commands = {
            # double[] getMotorLimits(String)
            "getMotorLimits": ("double[]", "String", self._do_get_motor_limits),
            # int startSetPhase(Phase)
            "startSetPhase": ("int", "Phase", self._do_start_set_phase),
            # int startRasterScan(double, double, int, int, boolean, boolean, boolean)
            "startRasterScan": (
                "int",
                "double, double, int, int, boolean, boolean, boolean",
                self._do_start_raster_scan,
            ),
            # int startScanEx(int, double, double, double, int)
            "startScanEx": (
                "int",
                "int, double, double, double, int",
                self._do_start_scan_ex,
            ),
            # int startScan4DEx(double, double, double, double, double, double,
            #                   double, double, double, double, double)
            "startScan4DEx": (
                "int",
                "double, double, double, double, double, double, double, double, double, double, double",
                self._do_start_scan_4d_ex,
            ),
            # boolean isTaskRunning(int)
            "isTaskRunning": ("boolean", "int", self._do_is_task_running),
            # String[] getTaskInfo(int)
            "getTaskInfo": ("String[]", "int", self._do_get_task_info),
            # void saveCentringPositions()
            "saveCentringPositions": ("void", "", self._do_save_centring_positions),
            # double[] getMotorDynamicLimits(String)
            "getMotorDynamicLimits": (
                "double[]",
                "String",
                self._do_get_motor_dynamic_limits,
            ),
            # void abort()
            "abort": ("void", "", self._do_abort),
            # Position getBeamstopPosition()
            "getBeamstopPosition": ("Position", "", self._do_get_beamstop_position),
            # Position setBeamstopPosition(Position)
            "setBeamstopPosition": (
                "Position",
                "Position",
                self._do_set_beamstop_position,
            ),
        }

        # add an internal attributes watcher, to deal with zoom changes
        self.add_attribute_updated_callback(self._attribute_updated)

    def _attribute_updated(self, name: str, attr: Any, timestamp: int):
        """
        This callback watches for zoom level changes and updates camera scale attributes.
        """
        if name != "CoaxialCameraZoomValue":
            # we only care about CoaxialCameraZoomValue, aka zoom level changes
            return

        #
        # Here we know that it's the CoaxialCameraZoomValue attribute changed.
        # Update the CoaxCamScale attributes to match new zoom level.
        #

        zoom_level = attr.val
        coax_cam_scale = COAX_CAM_SCALES[zoom_level - 1]

        self.write_attribute("CoaxCamScaleX", coax_cam_scale.x, timestamp)
        self.write_attribute("CoaxCamScaleY", coax_cam_scale.y, timestamp)

    def _fast_shutter_direct_beam_check(self, new_value: bool):
        """Checks for a situation when an attempt is made to open fast shutter, with beamstop out of BEAM position.

        Args:
            new_value: new value for fastShutterIsOpen attribute

        Raises:
            DisallowedState: When opening fast shutter could lead to direct beam on the detector.

        Returns:
            new value for fastShutterIsOpen attribute. Here it's always the same as the input value.
        """
        direct_beam_enabled = self._attrs["DirectBeamEnabled"].val
        beamstop_position = self._attrs["BeamstopPosition"].val
        if not direct_beam_enabled and new_value and beamstop_position != "BEAM":
            raise DisallowedState("Cannot change value to: true")
        return new_value

    def _move_beamstop_check(self, new_position: str):
        """Checks for an attempt of moving beamstop when fast shutter is open and direct beam is not allowed.

        Args:
            new_position: New position for the beamstop.

        Raises:
            DisallowedState: Thrown when moving beamstop could lead to direct beam on the detector.

        Returns:
            new position for the beamstop. Here it's always the same as the input
        """
        direct_beam_enabled = self._attrs["DirectBeamEnabled"].val
        fast_shutter_is_open = self._attrs["FastShutterIsOpen"].val

        if not direct_beam_enabled and fast_shutter_is_open:
            # This is error message MD3UP generates when beamstop is moved while fast shutter is open.
            raise DisallowedState("Invalid value")

        return new_position

    def _add_task(self, name: str, running_time: float):
        def get_synchronization_id():
            self._synchronization_id += 1
            return self._synchronization_id

        task_id = get_synchronization_id()
        now = time()
        self._tasks[task_id] = Task(name, now, now + running_time)

        return task_id

    def _get_task(self, task_id: str) -> Task:
        task_id = int(task_id)
        task = self._tasks.get(task_id)
        if task is None:
            raise CommandError(f"Invalid task: {task_id}")

        return task

    def _do_get_motor_limits(self, motor_name) -> tuple[float, float]:
        return self._motors[motor_name]

    def _do_start_set_phase(self, phase) -> int:
        async def update_current_phase():
            self.write_attribute("CurrentPhase", "Unknown")
            await asyncio.sleep(PHASE_CHANGE_TIME_SEC)
            self.write_attribute("CurrentPhase", phase)
            if phase == "DataCollection":
                self.write_attribute("BeamstopPosition", "BEAM")

        if phase not in PHASES:
            # MD3 error message when unexpected phase specified
            raise CommandError(
                "No method with the correct signature: true.startSetPhase"
            )

        asyncio.create_task(update_current_phase())
        return self._add_task(f"Set {phase.upper()} PHASE", PHASE_CHANGE_TIME_SEC + 0.1)

    def _do_start_raster_scan(
        self,
        _vertical_range,
        _horizontal_range,
        _vert_num_frames,
        _horiz_num_frames,
        _enable_reverse_direction,
        _use_centring_table,
        _fast_scan,
    ) -> int:
        return self._add_task("Start RASTER SCAN", 5.2)

    def _do_start_scan_ex(
        self,
        _frame_id,
        _start_angle,
        _scan_range,
        _exposure_time,
        _number_of_passes,
    ) -> int:
        return self._add_task("Start SCAN", 3.2)

    def _do_start_scan_4d_ex(self, *_):
        return self._add_task("Start 4D-SCAN", 3.2)

    def _do_is_task_running(self, task_id) -> bool:
        task = self._get_task(task_id)
        return task.is_running()

    def _do_get_task_info(self, task_id):
        def get_reply_vals():
            if task.is_running():
                return "", "", "", ""

            # finished, aka not running
            return epoch_as_text(task.end_time), "true", "null", "1"

        task = self._get_task(task_id)
        end_time, result, exception, result_id = get_reply_vals()

        return [
            task.name,
            "8",
            epoch_as_text(task.start_time),
            end_time,
            result,
            exception,
            result_id,
        ]

    def _do_save_centring_positions(self):
        # this is NOP for now
        pass

    def _do_abort(self):
        # this is NOP for now
        pass

    def _do_get_beamstop_position(self):
        return self._attrs["BeamstopPosition"].val

    def _do_set_beamstop_position(self, position):
        
        # Performs a check if moving beamstop could lead to direct beam hitting the detector.
        # It is already present in the setter of BeamstopPosition attribute, but it makes things 
        # easier by calling it also there, as the setting of attribute occurs inside a task.
        self._move_beamstop_check(position)

        async def update_beamstop_pos():
            self.write_attribute("BeamstopPosition", "UNKNOWN")
            await asyncio.sleep(BEAMSTOP_TRAVEL_TIME_SEC)
            self.write_attribute("BeamstopPosition", position)

        if position not in BEAMSTOP_POSITIONS:
            # MD3 error message when unexpected position specified
            raise CommandError(
                "No method with the correct signature: true.setBeamstopPosition"
            )

        cur_pos = self._attrs["BeamstopPosition"].val

        if cur_pos == "UNKNOWN":
            # beam-stop is currently moving
            raise CommandError("Cannot execute command: motor is moving")

        if cur_pos == position:
            # already at requested position, NOP
            return

        asyncio.create_task(update_beamstop_pos())

    def _do_get_motor_dynamic_limits(self, _motor_name: str):
        # return some plausible dummy values for now
        return [-2.97366048458438, 2.970646846947152]

    def add_attribute_updated_callback(
        self, attribute_update_cb: AttributeUpdatedCallback
    ):
        self._attr_updated_callbacks.add(attribute_update_cb)

    def remove_attribute_updated_callback(
        self, attribute_update_cb: AttributeUpdatedCallback
    ):
        self._attr_updated_callbacks.remove(attribute_update_cb)

    def get_motor_name(self, attribute_name: str) -> Optional[str]:
        """
        For a motor position attributes, returns the motor name.
        If not a motor position attribute, return None.

        For example returns 'Omega' for 'OmegaPosition', and for 'FooBarAttribute' returns None.
        """
        if not attribute_name.endswith("Position"):
            return None

        motor_name = attribute_name[: -len("Position")]
        if motor_name not in self._motors:
            # does not seem to be a motor
            return None

        return motor_name

    def get_attribute(self, attribute_name: str) -> Attribute:
        attr = self._attrs.get(attribute_name)
        if attr is None:
            raise UnknownAttribute()

        return attr

    def write_attribute(
        self, attribute_name: str, attribute_value, timestamp: None | int = None
    ):
        if timestamp is None:
            timestamp = int(time())

        attr = self.get_attribute(attribute_name)
        attr.val = attribute_value

        for attr_cb in self._attr_updated_callbacks:
            attr_cb(attribute_name, attr, timestamp)

        return attr

    def list_commands(self):
        for name, (ret_type, args, _) in self._commands.items():
            yield name, ret_type, args

    def exec_command(self, command_name, command_args):
        cmd = self._commands.get(command_name)
        if cmd is None:
            raise UnknownCommand()

        _, _, cmd_method = cmd
        return cmd_method(*command_args)


class Exporter:
    def __init__(self):
        self._md3 = MD3Up()

    async def _write_reply(self, writer: SynchronizedWriter, reply: str):
        msg = STX + reply.encode() + ETX

        await writer.write_drain(msg)

        log(f"< {msg}")

    async def _read_message(self, reader: StreamReader) -> str:
        message = await reader.readuntil(ETX)

        log(f"> {message}")

        # assert that message starts with STX byte
        assert message[0] == STX[0]

        # chop off STX and ETX bytes
        return message[1:-1].decode()

    async def _send_evt_message(
        self, writer: SynchronizedWriter, attr_name, attr_val, attr_type, timestamp
    ):
        val = encode_val(attr_val)
        msg = f"EVT:{attr_name}\t{val}\t{timestamp}\t{attr_type}"
        await self._write_reply(writer, msg)

    def _attribute_updated(
        self,
        writer: SynchronizedWriter,
        attr_name: str,
        attr: Attribute,
        timestamp: int,
    ):
        asyncio.create_task(
            self._send_evt_message(writer, attr_name, attr.val, attr.type, timestamp)
        )

    async def _move_motor(
        self, writer: SynchronizedWriter, motor_name: str, new_pos: float
    ):
        motor_pos_attr = f"{motor_name}Position"
        motor_state_attr = f"{motor_name}State"

        start_pos = self._md3.get_attribute(motor_pos_attr).val
        step = (new_pos - start_pos) / MOTOR_STEPS

        self._md3.write_attribute(motor_state_attr, "Moving")

        for n in range(1, MOTOR_STEPS + 1):
            step_pos = start_pos + (n * step)

            # Omega is a rotation angle motor, thus a special case.
            # MD3 automatically wraps any set value within 0..360 degrees range.
            if motor_name == "Omega":
                step_pos = step_pos % 360.0

            self._md3.write_attribute(motor_pos_attr, step_pos)
            await asyncio.sleep(2 / MOTOR_STEPS)

        self._md3.write_attribute(motor_state_attr, "Ready")

    def _handle_read(self, attr_name: str) -> str:
        try:
            attr = self._md3.get_attribute(attr_name)
            return f"RET:{encode_val(attr.val)}"
        except UnknownAttribute:
            log(f"WARNING: read command for an unknown attribute '{attr_name}'")
            # this seems to be the error message MD3UP generates for unknown attributes
            return f"ERR:Undefined method: true.get{attr_name}"

    def _handle_write(self, slug: str, writer: SynchronizedWriter) -> str:
        name, val = slug.split(" ", 2)
        attr_type = type(self._md3.get_attribute(name).val)
        val = parse_val(attr_type, val)

        motor_name = self._md3.get_motor_name(name)
        try:
            if motor_name is None:
                # write non-motor attribute
                self._md3.write_attribute(name, val)
            else:
                # this is a motor position attribute, emulate moving motor
                asyncio.create_task(self._move_motor(writer, motor_name, val))
        except DisallowedState as invalid_state_err:
            return f"ERR:{str(invalid_state_err)}"
        return "NULL"

    def _handle_exec(self, command: str) -> str:
        cmd_name, args = command.split(" ", 1)
        if args == "":
            # no arguments specified
            args = []
        else:
            args = args.strip().split("\t")

        try:
            ret = self._md3.exec_command(cmd_name, args)
        except CommandError as cmd_err:
            return f"ERR:{str(cmd_err)}"
        except DisallowedState as invalid_state_err:
            return f"ERR:{str(invalid_state_err)}"

        return f"RET:{encode_val(ret)}"

    def _handle_list(self) -> str:
        def commands():
            for name, ret_type, args in self._md3.list_commands():
                yield f"{ret_type} {name}({args})"

        cmds = "\t".join(list(commands()))

        return f"RET:{cmds}"

    async def _send_initial_events(self, writer: SynchronizedWriter):
        async def send_message(attr_name, msg_name):
            attr = self._md3.get_attribute(attr_name)
            await self._send_evt_message(
                writer, msg_name, attr.val, attr.type, timestamp
            )

        timestamp = int(time())

        await send_message("State", "State")
        await send_message("Status", "Status")

        for name in INITIAL_EVENTS:
            state = f"{name}State"
            position = f"{name}Position"
            await send_message(state, state)
            await send_message(position, state)

        await send_message("DetectorState", "DetectorState")
        await send_message("DetectorDistance", "DetectorState")

        # MD3 sends CurrentApertureDiameterIndex event twice for some reason
        await send_message(
            "CurrentApertureDiameterIndex", "CurrentApertureDiameterIndex"
        )
        await send_message(
            "CurrentApertureDiameterIndex", "CurrentApertureDiameterIndex"
        )

    async def _handle_message(self, msg: str, writer: SynchronizedWriter):
        def get_reply():
            if msg.startswith(READ):
                return self._handle_read(msg[len(READ) :])

            if msg.startswith(WRTE):
                return self._handle_write(msg[len(WRTE) :], writer)

            if msg.startswith(EXEC):
                return self._handle_exec(msg[len(EXEC) :])

            if msg.startswith(LIST):
                return self._handle_list()

            if msg.startswith(NAME):
                return "RET:MD"

            assert False, f"unexpected message '{msg}'"

        await self._write_reply(writer, get_reply())

    async def new_connection(self, reader: StreamReader, writer: StreamWriter):
        log("MD3 new connection")

        sync_writer = SynchronizedWriter(writer)
        attrs_update_callback = lambda name, attr, timestamp: self._attribute_updated(
            sync_writer, name, attr, timestamp
        )
        self._md3.add_attribute_updated_callback(attrs_update_callback)

        await self._send_initial_events(sync_writer)

        try:
            while True:
                msg = await self._read_message(reader)
                await self._handle_message(msg, sync_writer)
        except asyncio.IncompleteReadError:
            self._md3.remove_attribute_updated_callback(attrs_update_callback)
            log("connection closed")
        except Exception as ex:
            log(f"error: {str(ex)}")
            traceback.print_exception(ex)


exporter = Exporter()
tcp_srv = AsyncTCPServer(PORT, exporter.new_connection)
log("MD3 exporter emulator starting")
tcp_srv.start()
