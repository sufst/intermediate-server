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
import asyncio

__all__ = ["run"]


config.init_config()
protocol.init_protocol()

emit_data = {
    "cloud": {
        "emulation": {}, "car": {}
    },
    "sufst_vm": {
        "emulation": {}, "car": {}
    }
}


def run():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(_run())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


async def _run():
    print("Starting app")
    await socket_io.start()
    await emulator.start()
    await protocol.start()
    print("Started app")


@socket_io.periodic_emitter("sufst_vm", "emulation")
async def on_periodic_emulation_emit():
    if not emit_data["sufst_vm"]["emulation"] == {}:
        await socket_io.sufst_vm.emit("data", emit_data["sufst_vm"]["emulation"], namespace="/emulation")
        emit_data["sufst_vm"]["emulation"] = {}


@socket_io.periodic_emitter("sufst_vm", "car")
async def on_periodic_emulation_emit():
    if not emit_data["sufst_vm"]["car"] == {}:
        await socket_io.sufst_vm.emit("data", emit_data["sufst_vm"]["car"], namespace="/car")
        emit_data["sufst_vm"]["car"] = {}


@emulator.emulation_consumer()
async def periodic_emulation_consumer(data):
    servers = ["cloud", "sufst_vm"]

    for server in servers:
        if config.socket_io[server]["namespaces"]["emulation"]["enable"]:
            for sensor, values in data.items():
                if sensor not in emit_data[server]["emulation"]:
                    emit_data[server]["emulation"][sensor] = []
                emit_data[server]["emulation"][sensor].append(values)


@socket_io.sufst_vm.on("connect", namespace="/emulation")
async def on_sufst_vm_emulation_connect():
    print(f"sufst_vm /emulation connected")
    await socket_io.sufst_vm.emit("config", config.sensors, namespace="/emulation")


@socket_io.sufst_vm.on("connect", namespace="/car")
async def on_sufst_vm_emulation_connect():
    print(f"sufst_vm /car connected")
    await socket_io.sufst_vm.emit("config", config.sensors, namespace="/car")


@protocol.on("connect")
async def on_protocol_connect():
    print("Protocol connected")


@protocol.on("disconnect")
async def on_protocol_disconnect(exc):
    print("Protocol disconnect")
    if exc is not None:
        print(exc)


def add_sensor_data_to_emit_data(sensor, data):
    servers = ["cloud", "sufst_vm"]

    for server in servers:
        if config.socket_io[server]["namespaces"]["car"]["enable"]:
            if sensor not in emit_data[server]["car"]:
                emit_data[server]["car"][sensor] = []
            emit_data[server]["car"][sensor].append(data)


@protocol.on("core")
async def on_protocol_core(core):
    for sensor, value in core.items():
        if not sensor == "epoch":
            add_sensor_data_to_emit_data(sensor, {"epoch": core["epoch"], "value": value})


@protocol.on("aero")
async def on_protocol_aero(aero):
    for sensor, value in aero.items():
        if not sensor == "epoch":
            add_sensor_data_to_emit_data(sensor, {"epoch": aero["epoch"], "value": value})


@protocol.on("diagnostic")
async def on_protocol_diagnostic(diagnostic):
    for sensor, value in diagnostic.items():
        if not sensor == "epoch":
            add_sensor_data_to_emit_data(sensor, {"epoch": diagnostic["epoch"], "value": value})


@protocol.on("power_train")
async def on_protocol_power_train(power_train):
    for sensor, value in power_train.items():
        if not sensor == "epoch":
            add_sensor_data_to_emit_data(sensor, {"epoch": power_train["epoch"], "value": value})


@protocol.on("suspension")
async def on_protocol_suspension(suspension):
    for sensor, value in suspension.items():
        if not sensor == "epoch":
            add_sensor_data_to_emit_data(sensor, {"epoch": suspension["epoch"], "value": value})


@protocol.on("misc")
async def on_protocol_misc(misc):
    for sensor, value in misc.items():
        if not sensor == "epoch":
            add_sensor_data_to_emit_data(sensor, {"epoch": misc["epoch"], "value": value})
