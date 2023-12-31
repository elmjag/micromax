#!/usr/bin/env python3
from typing import Optional
import sys
import traceback
import asyncio
from enum import Enum
from asyncio import StreamReader, StreamWriter, Event
from argparse import ArgumentParser
from overlord import Overlord

PUCKS_NUM = 29

DI = "di"
DO = "do"
ON = "on"
OFF = "off"
PUT = "put"
TRAJ = "traj"
ABORT = "abort"
STATE = "state"
RESET = "reset"
MESSAGE = "message"
OPENLID = "openlid"
CLOSELID = "closelid"
POSITION = "position"
CLEARMEMORY = "clearmemory"


def log(msg: str):
    print(msg)
    sys.stdout.flush()


async def _read_command(connection_name: str, reader: StreamReader) -> str:
    cmd = await reader.readuntil(b"\r")
    log(f"{connection_name}> {cmd}")

    # chop off trailing \r and make a string
    return cmd[:-1].decode()


async def _write_reply(connection_name: str, writer: StreamWriter, reply: str):
    reply = (reply + "\r").encode()
    writer.write(reply)
    await writer.drain()

    log(f"{connection_name}< {reply}")


def _encode_list(lst):
    encoded = [_encode(v) for v in lst]
    return ",".join(encoded)


def _encode(val):
    t = type(val)

    if t == bool:
        return "1" if val else "0"

    if t == list:
        return _encode_list(val)


def _get_command_args(command_name: str, command: str) -> list:
    args_str = command[len(command_name) + 1 : -1]
    return args_str.split(",")


class _Positions(Enum):
    HOME = "HOME"
    SOAK = "SOAK"


class _RobotArm:
    def __init__(self):
        self._position = _Positions.HOME

    def move_to(self, new_position: _Positions):
        assert self._position is not None
        asyncio.create_task(self._run_trajectory(new_position))

    async def _run_trajectory(self, new_position: _Positions):
        # start moving to new position
        log(f"moving to {new_position.value}")
        self._position = None

        # emulate that it take some time to reach destination position
        await asyncio.sleep(4)

        # we have arrived at our new position
        self._position = new_position
        log(f"reached {new_position.value}")

    def is_moving(self) -> bool:
        return self._position is None

    def get_position(self) -> _Positions:
        return self._position

    def get_position_name(self) -> str:
        if self._position is None:
            return "UNDEFINED"

        return self._position.value


class _DewarLid:
    OPEN_POS = 10
    CLOSED_POS = 0

    def __init__(self, overlord: Overlord):
        self._overlord = overlord
        self._position = self.OPEN_POS
        self._target_position = None
        self._target_position_set = Event()

        self._update_overlord_attributes()

    def start(self):
        asyncio.create_task(self._run())

    def is_moving(self) -> bool:
        return self._target_position is not None

    def _update_overlord_attributes(self):
        self._overlord.set_attr("dewarlid.position", self._position)
        self._overlord.set_attr("dewarlid.moving", self.is_moving())

    async def _run(self):
        async def move_lid():
            while self._position != self._target_position:
                step = 1 if self._position < self._target_position else -1
                self._position += step
                self._update_overlord_attributes()
                await asyncio.sleep(0.6)

            self._target_position = None
            self._target_position_set.clear()
            self._update_overlord_attributes()

        while True:
            await self._target_position_set.wait()
            await move_lid()

    def open(self):
        self._target_position = self.OPEN_POS
        self._target_position_set.set()

    def close(self):
        self._target_position = self.CLOSED_POS
        self._target_position_set.set()


class _IsaraMixin:
    """
    contains code shared by ISARA and ISARA2 emulation
    """

    def __init__(self):
        self._overlord = Overlord()
        self._message = "System OK for operation"
        #
        # emulates the robot PLC modes, i.e. the key switch modes
        #
        # we only emulate:
        #   'remote mode' (_remote_mode = True)
        #   'manual mode' (_remote_mode = False)
        #
        self._remote_mode = True
        self._door_closed = True
        self._power_on = True

        # puck present in the dewar
        self._dewar_pucks = [False] * PUCKS_NUM
        # start with a couple of pucks present, for convenience
        self._dewar_pucks[0] = True
        self._dewar_pucks[PUCKS_NUM - 1] = True

        self._robot_arm = _RobotArm()
        self._dewar_lid = _DewarLid(self._overlord)

        self._update_overlord_attributes()

    def _handle_state_command(self):
        # needs model specific implementation
        raise NotImplementedError()

    def _handle_di_command(self):
        # needs model specific implementation
        raise NotImplementedError()

    def _handle_do_command(self):
        # needs model specific implementation
        raise NotImplementedError()

    def _check_plc(self) -> Optional[str]:
        if not self._remote_mode:
            return "Remote mode requested"

        if not self._door_closed:
            return "Doors must be closed"

    def _handle_on_command(self) -> str:
        plc_err = self._check_plc()
        if plc_err is not None:
            return plc_err

        self._power_on = True
        return "on"

    def _handle_off_command(self) -> str:
        plc_err = self._check_plc()
        if plc_err is not None:
            return plc_err

        self._power_on = False
        return "off"

    def _handle_message_command(self) -> str:
        return "System OK for operation"

    def _handle_operate_command(self, command: str) -> str:
        if command == ON:
            return self._handle_on_command()
        if command == OFF:
            return self._handle_off_command()
        if command == ABORT:
            return "abort"

        assert False, f"unexpected command {command} on operate connection"

    def _handle_monitor_command(self, command: str) -> str:
        if command == STATE:
            return self._handle_state_command()
        if command == DI:
            return self._handle_di_command()
        if command == DO:
            return self._handle_do_command()
        if command == MESSAGE:
            return self._handle_message_command()

        assert False, f"unexpected command {command} on monitor connection"

    async def _new_operate_connection(self, reader: StreamReader, writer: StreamWriter):
        log("new operate connection")
        try:
            while True:
                cmd = await _read_command("operate", reader)
                reply = self._handle_operate_command(cmd)

                await _write_reply("operate", writer, reply)
        except:
            print(traceback.format_exc())

    async def _new_monitor_connection(self, reader: StreamReader, writer: StreamWriter):
        log("new monitor connection")
        try:
            while True:
                cmd = await _read_command("monitor", reader)
                reply = self._handle_monitor_command(cmd)

                await _write_reply("monitor", writer, reply)
        except:
            print(traceback.format_exc())

    def _update_overlord_attributes(self):
        self._overlord.set_attr("dewar.pucks", self._dewar_pucks)
        self._overlord.set_attr("plc.remote_mode", self._remote_mode)
        self._overlord.set_attr("plc.door_closed", self._door_closed)

    def _handle_overlord_puck_command(self, puck_number: str, is_present: str):
        puck_number = int(puck_number)
        is_present = is_present == "true"
        if puck_number < 0 or puck_number > PUCKS_NUM:
            log(f"invalid puck number {puck_number}, ignoring")
            return

        self._dewar_pucks[puck_number] = is_present
        self._update_overlord_attributes()

    def _handle_overlord_remote_command(self, remote_enabled):
        remote_enabled = remote_enabled == "true"
        if self._remote_mode == remote_enabled:
            # same mode, ignore
            return

        self._remote_mode = remote_enabled
        # when flipping mode, robot is powered off
        self._power_on = False

        self._update_overlord_attributes()

    def _handle_overlord_door_closed_command(self, door_closed):
        self._door_closed = door_closed == "true"
        self._update_overlord_attributes()

    async def _process_overlord_commands(self):
        while True:
            command = await self._overlord.get_command()
            if command.name == "puck":
                self._handle_overlord_puck_command(*command.args)
            elif command.name == "remote":
                self._handle_overlord_remote_command(*command.args)
            elif command.name == "door_closed":
                self._handle_overlord_door_closed_command(*command.args)
            else:
                log(f"unexpected overlord command {command}, ignoring")

    async def start(self, overlord_port: int, operate_port: int, monitor_port: int):
        self._dewar_lid.start()
        asyncio.create_task(self._process_overlord_commands())

        op_srv = await asyncio.start_server(
            self._new_operate_connection, host="0.0.0.0", port=operate_port
        )

        mon_srv = await asyncio.start_server(
            self._new_monitor_connection, host="0.0.0.0", port=monitor_port
        )

        await asyncio.gather(
            op_srv.serve_forever(),
            mon_srv.serve_forever(),
            self._overlord.start(overlord_port),
        )


class Isara(_IsaraMixin):
    """
    emulates ISARA robot, the first model, aka the blue robot at BioMAX
    """

    def _handle_state_command(self) -> str:
        return f"state({_encode(self._power_on)},1,0,,,,,-1,-1,,,,0,0,,75.0,1.16,1.17,1.18,,,,)"

    def _handle_di_command(self) -> str:
        return "di(" + "0" * 99 + ")"

    def _handle_do_command(self) -> str:
        return "do(" + "0" * 99 + ")"

    def _handle_position_command(self) -> str:
        return "position(0.1,0.2,0.3,0.4,0.5,0.6)"

    def _handle_monitor_command(self, command: str) -> str:
        # handle ISARA1 specific monitor commands
        if command == POSITION:
            return self._handle_position_command()

        return super()._handle_monitor_command(command)


class Isara2(_IsaraMixin):
    """
    emulates ISARA2 robot, aka the yellow robot at MicroMAX
    """

    def _handle_state_command(self) -> str:
        power_on = _encode(self._power_on)
        position = self._robot_arm.get_position_name()
        path_running = _encode(self._robot_arm.is_moving())

        return (
            f"state({power_on},1,1,DoubleGripper,{position},,1,1,-1,-1,-1,-1,-1,"
            f"-1,-1,-1,,{path_running},0,75.0,0,0,0.3865678,75.0,72.0,1,0,0,"
            f"{self._message},67108864,152.9,-390.8,"
            "-17.3,-180.0,0.0,89.1,-75.6,-18.8,93.6,0.0,105.3,-165.5,,1,,1,0,0,0,0,"
            "0,0,0,0,0,0,0,0,0,changetool|3|3|0|-2.441|0.068|392.37|0.0|0.0|-0.984)"
        )

    def _handle_di_command(self) -> str:
        return (
            "di(0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,1,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,"
            "0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,"
            "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0)"
        )

    def _handle_do_command(self) -> str:
        puck_presence = _encode(self._dewar_pucks)

        return (
            "do("
            "0,0,1,0,0,1,0,1,0,0,"  #  0 -  9
            "1,0,0,0,0,0,0,0,0,0,"  # 10 - 19
            "0,0,0,1,0,0,0,0,0,0,"  # 20 - 29
            "0,0,0,0,0,0,0,0,0,0,"  # 30 - 39
            "0,0,0,1,0,0,0,0,0,0,"  # 40 - 49
            f"1,0,0,0,0,0,{puck_presence},0,0,0,0,0,"  # 50 - 89
            "0,0,0,0,0,0,0,0,0,0,"  # 90 - 99
            "0,0,0,0,0,0,0,0,0,0,"  # 100 - 110
            "0,0)"
        )

    def _handle_put_traj(self) -> str:
        if self._robot_arm.get_position() != _Positions.SOAK:
            return "Rejected - Trajectory must start at position: SOAK"

        return "put"

    def _handle_traj_command(self, name, *_) -> str:
        if not self._power_on:
            return "Robot power disabled"

        if self._robot_arm.is_moving():
            return "Path already running"

        if self._dewar_lid.is_moving():
            return "Disabled when lid is moving"

        if name == "soak":
            self._robot_arm.move_to(_Positions.SOAK)
            return "soak"

        if name == "home":
            self._robot_arm.move_to(_Positions.HOME)
            return "home"

        if name == "back":
            return "back"

        if name == "put":
            return self._handle_put_traj()

        raise NotImplementedError(f"running trajectory '{name}'")

    def _handle_openlid_command(self) -> str:
        self._dewar_lid.open()
        return "openlid"

    def _handle_closelid_command(self) -> str:
        self._dewar_lid.close()
        return "closelid"

    def _handle_clearmemory_command(self) -> str:
        if self._robot_arm.is_moving():
            return "Disabled when path is running"

        return "clearmemory"

    def _handle_reset_command(self) -> str:
        return "reset"

    def _handle_operate_command(self, command: str) -> str:
        #
        # handle ISARA2 specific operate commands
        #

        if command.startswith(TRAJ):
            args = _get_command_args(TRAJ, command)
            return self._handle_traj_command(*args)

        if command == OPENLID:
            return self._handle_openlid_command()

        if command == CLOSELID:
            return self._handle_closelid_command()

        if command == CLEARMEMORY:
            return self._handle_clearmemory_command()

        if command == RESET:
            return self._handle_reset_command()

        # handle generic operate commands
        return super()._handle_operate_command(command)


async def _listen(model: str, overlord_port: int, operate_port: int, monitor_port: int):
    def init_model():
        classes = {"ISARA": Isara, "ISARA2": Isara2}
        klass = classes[model]

        return klass()

    isara = init_model()

    log(
        f"emulating {model} API\n"
        f" overlord port: {overlord_port}\n"
        f" operate port: {operate_port}\n"
        f" monitor port: {monitor_port}"
    )

    await isara.start(overlord_port, operate_port, monitor_port)


def _parse_args():
    parser = ArgumentParser(description="Emulate ISARA Sample Changer API")

    parser.add_argument(
        "-o",
        "--operate-port",
        default=10000,
    )

    parser.add_argument(
        "-m",
        "--monitor-port",
        default=1000,
    )

    parser.add_argument(
        "--overlord-port",
        default=1111,
    )

    parser.add_argument(
        "--model",
        choices=["ISARA", "ISARA2"],
        default="ISARA2",
    )

    return parser.parse_args()


def _main():
    args = _parse_args()
    asyncio.run(
        _listen(args.model, args.overlord_port, args.operate_port, args.monitor_port)
    )


_main()
