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
import asyncio
import time

__all__ = ["emulator"]


class Modules:
    def __init__(self, modules):
        self.__dict__ = modules


class Emulation:
    consumers = []
    x = 0

    async def _periodic_task(self):
        while True:
            await asyncio.sleep(config.emulation["interval"])
            self._generate_next_emit_data()

            for consumer in self.consumers:
                await consumer(self.data)

    def _generate_next_emit_data(self):
        self.data = {}
        mods = {}
        for module in config.emulation["modules"]:
            mods[module] = __import__(module)

        mods = Modules(mods)
        now = time.time()

        for sensor, conf in config.sensors.items():
            self.data[sensor] = {
                "value": (lambda modules, x: eval(conf["emulation"]))(mods, self.x),
                "epoch": now
            }
        self.x += 1

    def emulation_consumer(self):
        def wrapper(func):
            self.consumers.append(func)
        return wrapper

    async def start(self):
        print("Starting emulation")
        asyncio.get_running_loop().create_task(self._periodic_task())
        print("Started emulation")


emulator = Emulation()
