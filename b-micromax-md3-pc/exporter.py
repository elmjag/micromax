#!/usr/bin/env python3
from typing import Optional
import asyncio
import sys
import math
import traceback
from time import time
from asyncio import StreamReader, StreamWriter, Lock
from datetime import datetime
from atcpserv import AsyncTCPServer
from dataclasses import dataclass

MOTOR_STEPS = 8
PORT = 9001

STX = b"\02"
ETX = b"\03"
ARRAY_SEP = "\x1f"

READ = "READ "
WRTE = "WRTE "
LIST = "LIST"
EXEC = "EXEC "

BEAMSTOP_TRAVEL_TIME_SEC = 2.6
BEAMSTOP_POSITIONS = ["PARK", "BEAM", "TRANSFER", "OFF"]


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


class UnknownAttribute(Exception):
    pass


class UnknownCommand(Exception):
    pass


class CommandError(Exception):
    pass


class SynchronizedWriter:
    def __init__(self, writer: StreamWriter):
        self._writer = writer
        self._lock = Lock()

    async def write_drain(self, msg):
        async with self._lock:
            self._writer.write(msg)
            await self._writer.drain()


@dataclass
class Task:
    name: str
    # times are in unix epoch seconds
    start_time: float
    end_time: float

    def is_running(self) -> bool:
        return self.end_time > time()


class MD3Up:
    def __init__(self):
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
        }

        self._attrs = {
            "AperturePosition": "BEAM",
            "ApertureDiameters": [5, 10, 15, 20, 50, 600],
            "AlignmentXPosition": 6.582e-06,
            "AlignmentXState": "Ready",
            "AlignmentYPosition": 9.362e-06,
            "AlignmentYState": "Ready",
            "AlignmentZPosition": 5.712e-05,
            "AlignmentZState": "Ready",
            "FrontLightIsOn": False,
            "BackLightIsOn": False,
            "FrontLightFactor": 0.9,
            "BackLightFactor": 1.6,
            "BeamstopDistancePosition": 6.863187356482003,
            "BeamstopZPosition": -94.59997163171106,
            "CapillaryPosition": "PARK",
            "OmegaPosition": 359.999979169585,
            "OmegaState": "Ready",
            "CentringXPosition": 1.746e-06,
            "CentringXState": "Ready",
            "CentringYPosition": 1.174e-05,
            "CentringYState": "Ready",
            "CurrentApertureDiameterIndex": 2,
            "CoaxialCameraZoomValue": 1,
            "CoaxCamScaleX": 0.0018851562499999997,
            "CoaxCamScaleY": 0.0018851562499999997,
            "TransferMode": "SAMPLE_CHANGER",
            "HeadType": "SmartMagnet",
            "SampleIsLoaded": False,
            "CurrentPhase": "Transfer",
            "ScanStartAngle": 246.798,
            "ScanExposureTime": 0.663,
            "ScanRange": 6.0,
            "ScanNumberOfFrames": 1,
            "ScintillatorVerticalPosition": -89.99992208163434,
            "AlignmentTablePosition": "TRANSFER",
            "BeamstopPosition": "PARK",
            "ScintillatorPosition": "UNKNOWN",
            "SampleHolderLength": 22.0,
            "CapillaryVerticalPosition": -93.49539792171772,
            "PlateLocation": "null",
            "CentringTableVerticalPosition": -1.174697170195887e-05,
            "FastShutterIsOpen": False,
            "CameraExposure": 40000.0,
            "LastTaskInfo": [
                "Hot Start",
                "0",
                "2023-08-04 10:41:57.125",
                "2023-08-04 10:41:57.325",
                "true",
                "null",
                "1",
            ],
            "State": "Ready",
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

    def _do_start_set_phase(self, _phase) -> int:
        return self._add_task(f"Set {_phase.upper()} PHASE", 2.3)

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
        return self._attrs["BeamstopPosition"]

    async def _update_beamstop_pos(self, new_position):
        await asyncio.sleep(BEAMSTOP_TRAVEL_TIME_SEC)
        self._attrs["BeamstopPosition"] = new_position

    def _do_set_beamstop_position(self, position):
        if position not in BEAMSTOP_POSITIONS:
            # MD3 error message when unexpected position specified
            raise CommandError(
                "No method with the correct signature: true.setBeamstopPosition"
            )

        cur_pos = self._attrs["BeamstopPosition"]

        if cur_pos == "UNKNOWN":
            # beam-stop is currently moving
            raise CommandError("Cannot execute command: motor is moving")

        if cur_pos == position:
            # already at requested position, NOP
            return

        self._attrs["BeamstopPosition"] = "UNKNOWN"
        asyncio.create_task(self._update_beamstop_pos(position))

    def _do_get_motor_dynamic_limits(self, _motor_name: str):
        # return some plausible dummy values for now
        return [-2.97366048458438, 2.970646846947152]

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

    def read_attribute(self, attribute_name: str):
        val = self._attrs.get(attribute_name)
        if val is None:
            raise UnknownAttribute()

        return val

    def write_attribute(self, attribute_name: str, attribute_value):
        if attribute_name not in self._attrs:
            raise UnknownAttribute()

        self._attrs[attribute_name] = attribute_value

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

    async def _update_attribute(self, writer: SynchronizedWriter, name: str, val):
        self._md3.write_attribute(name, val)

        timestamp = int(time())
        msg = f"EVT:{name}\t{val}\t{timestamp}\torg.embl.State"

        await self._write_reply(writer, msg)

    async def _move_motor(
        self, writer: SynchronizedWriter, motor_name: str, new_pos: float
    ):
        motor_pos_attr = f"{motor_name}Position"
        motor_state_attr = f"{motor_name}State"

        start_pos = self._md3.read_attribute(motor_pos_attr)
        step = (new_pos - start_pos) / MOTOR_STEPS

        await self._update_attribute(writer, motor_state_attr, "Moving")

        for n in range(1, MOTOR_STEPS + 1):
            step_pos = start_pos + (n * step)

            # Omega is a rotation angle motor, thus a special case.
            # MD3 automatically wraps any set value within 0..360 degrees range.
            if motor_name == "Omega":
                step_pos = step_pos % 360.0

            await self._update_attribute(writer, motor_pos_attr, step_pos)
            await asyncio.sleep(2 / MOTOR_STEPS)

        await self._update_attribute(writer, motor_state_attr, "Ready")

    def _handle_read(self, attr_name: str) -> str:
        try:
            val = self._md3.read_attribute(attr_name)
            return f"RET:{encode_val(val)}"
        except UnknownAttribute:
            log(f"WARNING: read command for an unknown attribute '{attr_name}'")
            # this seems to be the error message MD3UP generates for unknown attributes
            return f"ERR:Undefined method: true.get{attr_name}"

    def _handle_write(self, slug: str, writer: SynchronizedWriter) -> str:
        name, val = slug.split(" ", 2)
        attr_type = type(self._md3.read_attribute(name))
        val = parse_val(attr_type, val)

        motor_name = self._md3.get_motor_name(name)
        if motor_name is None:
            # this is a motor position attribute, emulate moving motor
            asyncio.create_task(self._update_attribute(writer, name, val))
        else:
            asyncio.create_task(self._move_motor(writer, motor_name, val))

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

        return f"RET:{encode_val(ret)}"

    def _handle_list(self) -> str:
        def commands():
            for name, ret_type, args in self._md3.list_commands():
                yield f"{ret_type} {name}({args})"

        cmds = "\t".join(list(commands()))

        return f"RET:{cmds}"

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

            assert False, f"unexpected message '{msg}'"

        await self._write_reply(writer, get_reply())

    async def new_connection(self, reader: StreamReader, writer: StreamWriter):
        log("MD3 new connection")

        sync_writer = SynchronizedWriter(writer)

        try:
            while True:
                msg = await self._read_message(reader)
                await self._handle_message(msg, sync_writer)
        except Exception as ex:
            log(f"error: {str(ex)}")
            traceback.print_exception(ex)


exporter = Exporter()
tcp_srv = AsyncTCPServer(PORT, exporter.new_connection)
log("MD3 exporter emulator starting")
tcp_srv.start()
