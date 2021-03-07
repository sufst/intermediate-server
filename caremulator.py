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
from xml.dom import minidom

import common
import serverdatabase


class CarEmulator:
    def __init__(self, database: serverdatabase.ServerDatabase, delay_s: float):
        """
        Initialise an instance of the car emulator.

        The car emulator will periodically insert dummy sensor data into the passed database at the wanted interval.
        It is recommended an emulator database is used rather than the real staging database so the real database
        does not contain fake car data.

        The emulations are extracted from the config_file (xml file) for each wanted sensor.

        :param database: The database to insert into.
        :param delay_s: The delay before inserting the dummy data in seconds (float).
        """
        self._database = database
        self._delay_s = delay_s
        self._running = True
        self._logger = common.get_logger("CarEmulator", "DEBUG")

        self._emulation_config = minidom.parse("caremulator_config.xml")
        self._sensors_config = self._emulation_config.getElementsByTagName("sensor")
        self._parameters_config = self._emulation_config.getElementsByTagName("delay")
        self._delay = int(self._parameters_config[0].firstChild.data)

        self._sensor_emulators = {}

        for sensor in self._sensors_config:
            self._sensor_emulators[sensor.attributes["name"].value] = sensor.firstChild.data

        for name, emulator in self._sensor_emulators.items():
            # We can assume the database for emulation is based in memory rather than a file database.
            # Either way, create the sensor tables in case they don't already exist.
            self._database.create_sensor_table(name, ["value"])

        self._logger.info("Configuration: "
                          f"\n\tdelay <- {self._delay}"
                          f"\n\tsensors <- {self._sensor_emulators}")

    def serve(self):
        """
        The asynchronous serving of the car emulator by periodically inserting dummy sensor data into the emulation
        database.

        Can be stopped by stopping the underlying event loop which is using used to serve or stopping the future.
        """

        asyncio.get_event_loop().create_task(self._serve())

    async def _serve(self):
        x = 0

        while True:
            await asyncio.sleep(self._delay)

            epoch = time.time()

            # Get all the emulator for each sensor and then eval (runs the emulator string as Python code) the emulator
            # formula.
            for name, emulator in self._sensor_emulators.items():
                value = eval(emulator)
                self._logger.debug(f"{name} <- {value}")
                self._database.insert_sensor_data(name, epoch, (value,))

            self._database.commit()

            x += 1
