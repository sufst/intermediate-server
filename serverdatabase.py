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

import sqlite3


def _get_comma_separated_entry(entries: tuple or list) -> str:
    entries_str = ""
    for entry in entries:
        entries_str = f"{entries_str}{entry},"

    # Remove the trailing ","
    return entries_str[:-1]


class ServerDatabase:
    def __init__(self, name: str):
        """
        The ServerDatabase provides helper functions for accessing the SQLite 3 database which is used as a staging
        ground for sensor data between the sensor data producer (the car) and sensor data consumers (front-end).

        :param name: The name of the database to use.
        """
        self._name = name
        self._create_database()

    def _create_database(self):
        self._con = sqlite3.connect(f"{self._name}.db")

    def create_sensor_table(self, sensor: str, columns: list) -> None:
        """
        Create the sensor tables in the server database.
        :param sensor: The sensor name.
        :param columns: The column names for each sensor (minus the time column).
        :return: None
        """
        cur = self._con.cursor()

        # Create the table if they do not exist already.
        cur.execute(f"CREATE TABLE IF NOT EXISTS {sensor} (time,{_get_comma_separated_entry(columns)})")

    def insert_sensor_data(self, sensor: str, time: float, data: tuple) -> None:
        """
        Insert sensor data in the database.
        :param time: The timestamp of the data in the format of Epoch.
        :param sensor: The sensor name to insert into.
        :param data: The sensor data to insert.
        :return: None
        """
        cur = self._con.cursor()

        cur.execute(f"INSERT INTO {sensor} VALUES ({time},{_get_comma_separated_entry(data)})")

    def select_sensor_data_between_times(self, sensor: str, times: list) -> list:
        """
        Get sensor data between two times points from the sensor table (time column included)
        :param sensor: The sensor to select from.
        :param times: The times [low, high] to get data between.
        :return A list of sensor data tuples for between the times.
        """
        data = []
        cur = self._con.cursor()

        for row in cur.execute(f"SELECT * FROM {sensor} WHERE time BETWEEN {times[0]} AND {times[1]}"):
            data.append(row)

        return data

    def select_sensor_data_top_n_entries(self, sensor: str, n: int) -> list:
        """
        Get top n sensor data points from the sensor table (time column included)
        :param sensor: The sensor to select from.
        :param n The maximum number of rows to return.
        :return A list of sensor data tuples for up to the last n points.
        """
        data = []
        cur = self._con.cursor()

        for row in cur.execute(f"SELECT * FROM {sensor} ORDER BY time DESC LIMIT {n}"):
            data.append(row)

        return data

    def select_sensor_data_top_n_entries_and_between_times(self, sensor: str, n: int, times: list) -> list:
        """
        Get top n sensor data points from the sensor table between time times (time column included)
        :param sensor: The sensor to select from.
        :param n The maximum number of rows to return.
        :param times The times between to select from.
        :return A list of sensor data tuples for up to the last n points.
        """
        data = []
        cur = self._con.cursor()

        for row in cur.execute(
                f"SELECT * FROM {sensor} WHERE time BETWEEN {times[0]} AND {times[1]} ORDER BY time DESC LIMIT {n}"):
            data.append(row)

        return data

    def commit(self):
        """
        Commit the database to file.
        """
        self._con.commit()
