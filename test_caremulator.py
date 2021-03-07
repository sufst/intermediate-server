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
import sqlite3
import unittest

import caremulator
import serverdatabase


class TestCarEmulatorOverride(serverdatabase.ServerDatabase):
    def _create_database(self):
        self._con = sqlite3.connect(":memory:")


async def _check_test_database(database: TestCarEmulatorOverride):
    # Very crude test of run the emulator for a while and then see if the database has had values added to it.
    await asyncio.sleep(5)

    sensor_data = database.select_sensor_data_top_n_entries("rpm", 10)

    asyncio.get_running_loop().stop()

    print(sensor_data)

    if len(sensor_data) == 0:
        raise Exception


class TestCarEmulator(unittest.TestCase):
    def test_emulator_db_insertion(self):
        db = TestCarEmulatorOverride("None")

        emulator = caremulator.CarEmulator(db, 0.5)
        emulator.serve()
        asyncio.get_event_loop().create_task(_check_test_database(db))

        asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    unittest.main()
