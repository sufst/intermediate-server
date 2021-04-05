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
from time import time
from scheduler import scheduler, IntervalTrigger

__all__ = ["emulator"]


class Modules:
    def __init__(self, modules):
        self.__dict__ = modules


class Emulation:
    consumers = []
    x = 0
    data = {}
    job = None

    def _invoke_consumers(self):
        self._generate_next_emit_data()

        for consumer in self.consumers:
            consumer(self.data)

    def _generate_next_emit_data(self):
        self.data = {}
        mods = {}
        for module in config.emulation["modules"]:
            mods[module] = __import__(module)

        mods = Modules(mods)
        now = round(time(), 3)

        for sensor, conf in config.sensors.items():
            self.data[sensor] = {
                "value": (lambda modules, x: eval(conf["emulation"]))(mods, self.x),
                "epoch": now
            }
        self.x += 1

    def start(self):
        print("Starting emulation")
        scheduler.add_job(self._invoke_consumers, IntervalTrigger(seconds=config.emulation["interval"]))
        print("Started emulation")

    def register_consumer(self, func):
        self.consumers.append(func)


emulator = Emulation()
