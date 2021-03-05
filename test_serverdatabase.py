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

            time_s = int(time.time())
            database.insert_sensor_data(sensor, time_s, (value,))

            sensor_data = database.select_sensor_data_between_times(sensor, [time_s - 5, time_s])
            sensor_time, sensor_val = sensor_data[0]
            self.assertEqual(sensor_val, value)

    def test_commit(self):
        test_vectors = [("sense0", 1234), ("sense1", 4321)]

        database = serverdatabase.ServerDatabase("test_database")

        time_s = int(time.time())

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
