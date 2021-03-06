"""
    Southampton University Formula Student Team Intermediate Server
    Copyright (C) 2021 Nathan Rowley-Smith

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
import os
import time
import unittest

import serverdatabase


class TestServerDatabase(unittest.TestCase):
    def test_initialise(self):
        serverdatabase.ServerDatabase("test_database")
        self.assertTrue(os.path.isfile("test_database.db"))

    def test_sensors_table(self):
        test_vectors = [("sense0", 1234), ("sense1", 4321)]

        database = serverdatabase.ServerDatabase("test_database")

        for vec in test_vectors:
            sensor, value = vec

            database.create_sensor_table(sensor, ["value"])

            time_s = time.time()
            database.insert_sensor_data(sensor, time_s, (value,))

            sensor_data = database.select_sensor_data_between_times(sensor, [time_s - 5, time_s])
            sensor_time, sensor_val = sensor_data[0]
            self.assertEqual(sensor_val, value)

    def test_sensors_n_points(self):
        test_vectors_in = [("sense0", 1234), ("sense0", 4320),
                           ("sense0", 6789), ("sense0", 9876)]
        test_vectors_out = [("sense0", 9876), ("sense0", 6789)]

        database = serverdatabase.ServerDatabase("test_database")

        for vec in test_vectors_in:
            sensor, value = vec

            database.create_sensor_table(sensor, ["value"])

            time_s = time.time()
            database.insert_sensor_data(sensor, time_s, (value,))

        sensor_data = database.select_sensor_data_top_n_entries("sense0", len(test_vectors_out))

        self.assertTrue(len(sensor_data) == len(test_vectors_out))

        for row, vec in zip(sensor_data, test_vectors_out):
            sensor_time, sensor_val = row
            sensor, value = vec

            self.assertEqual(sensor_val, value)

    def test_commit(self):
        test_vectors = [("sense0", 1234), ("sense1", 4321)]

        database = serverdatabase.ServerDatabase("test_database")

        time_s = time.time()

        for vec in test_vectors:
            sensor, value = vec

            database.create_sensor_table(sensor, ["value"])
            database.insert_sensor_data(sensor, time_s, (value,))

        database.commit()

        del database

        database = serverdatabase.ServerDatabase("test_database")

        for vec in test_vectors:
            sensor, value = vec

            sensor_data = database.select_sensor_data_between_times(sensor, [time_s - 5, time_s])
            sensor_time, sensor_val = sensor_data[0]
            self.assertEqual(sensor_val, value)


if __name__ == '__main__':
    unittest.main()
