"""
    Southampton University Formula Student Team Intermediate Server
    Copyright (C) 2020 Nathan Rowley-Smith

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from configuration import config
from socket_io import socket_io
from emulation import emulator
from protocol import protocol
from scheduler import scheduler
import asyncio


__all__ = ["run"]

config.init_config()
protocol.init_protocol()


def run():
    print("Starting")

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    try:
        print("Starting scheduler")
        scheduler.start()
        print("Started scheduler")

        socket_io.start()
        emulator.start()
        protocol.start()

        loop.run_forever()
    except Exception as error:
        print(repr(error))
        print("Stopping")
        loop.stop()

    print("Stopped")


@protocol.on("connect")
def _on_protocol_connect():
    print("Protocol connected")


@protocol.on("disconnect")
def _on_protocol_disconnect(exc):
    print("Protocol disconnect")
    if exc is not None:
        print(exc)
