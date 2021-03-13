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

import asyncio
import time
import xml.etree.ElementTree

import common
import serverdatabase
import math
import random
import threading
import queue


class CarEmulator:
    def __init__(self, database: serverdatabase.ServerDatabase):
        """
        Initialise an instance of the car emulator.

        The car emulator will periodically insert dummy sensor data into the passed database at the wanted interval.
        It is recommended an emulator database is used rather than the real staging database so the real database
        does not contain fake car data.

        The emulations are extracted from the config_file (xml file) for each wanted sensor.

        :param database: The database to insert into.
        """
        self._database = database
        self._running = True
        self._queue = queue.Queue()

        self._parse_configuration()

        self._logger = common.get_logger("CarEmulator", self._config["verbose"])
        self._logger.info(f"Configuration: {self._config}")

    def _parse_configuration(self):
        config_root = xml.etree.ElementTree.parse("config.xml").getroot()
        self._config = {}

        for field in config_root.iter("emulation"):
            for config in field.findall("config"):
                if config.attrib["name"] == "sensors":
                    self._config[config.attrib["name"]] = {}
                    for sensor in config.findall("sensor"):
                        self._config[config.attrib["name"]][sensor.attrib["name"]] = sensor.text
                else:
                    self._config[config.attrib["name"]] = config.text

        assert("sensors" in self._config)
        assert(len(self._config["sensors"]) > 0)
        assert("delay" in self._config)
        assert("verbose" in self._config)

        self._config["delay"] = float(self._config["delay"])

    def serve(self):
        """
        The asynchronous serving of the car emulator by periodically inserting dummy sensor data into the emulation
        database.

        Can be stopped by stopping the underlying event loop which is using used to serve or stopping the future.
        """

        threading.Thread(target=self._serve_thread).start()
        asyncio.get_event_loop().create_task(self._serve_emulator())

    async def _serve_emulator(self):
        while True:
            if not self._queue.empty():
                name, epoch, (value,) = self._queue.get_nowait()
                self._database.insert_sensor_data(name, epoch, (value,))
            else:
                await asyncio.sleep(self._config["delay"])

    def _serve_thread(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        asyncio.get_event_loop().create_task(self._serve())
        asyncio.get_event_loop().run_forever()

    async def _serve(self):
        x = 0

        while True:
            await asyncio.sleep(self._config["delay"])

            epoch = time.time()

            # Get all the emulator for each sensor and then eval (runs the emulator string as Python code) the emulator
            # formula.
            for name, emulator in self._config["sensors"].items():
                value = eval(emulator)
                self._logger.debug(f"{name} <- {value}")
                self._queue.put((name, epoch, (value,)))

            x += 1


