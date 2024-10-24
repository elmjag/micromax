#!/usr/bin/env python3
import socket
import sys

HOST = "b-micromax-md3-pc"
PORT = 9001

COMMANDS = {
    "back_on": b"\x02WRTE BackLightIsOn True\x03",
    "back_off": b"\x02WRTE BackLightIsOn False\x03",
    "front_on": b"\x02WRTE FrontLightIsOn True\x03",
    "front_off": b"\x02WRTE FrontLightIsOn False\x03",
}


def usage():
    print(f"{sys.argv[0]} <command>\n\ncommands:")
    for cmd in COMMANDS:
        print(f"    {cmd}")

    sys.exit()


def get_command():
    if len(sys.argv) != 2:
        usage()

    command = sys.argv[1].lower()
    if command not in COMMANDS:
        usage()

    return COMMANDS[command]


def main():
    command = get_command()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(command)
        while True:
            print(s.recv(1024))


main()
