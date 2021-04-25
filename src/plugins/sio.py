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
from helpers import config
import socketio
import requests
import json

client = socketio.Client(reconnection=False)
conf = config.config['sio']


def connect():
    try:
        print(f"Attempting {conf['Url']}/login")
        response = requests.post(
            f"{conf['Url']}/login",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "username": "intermediate-server",
                "password": "sufst"
            }), timeout=10)
    except Exception as error:
        client.handlers['/']['error'](error)
    else:
        if response.status_code != 200:
            raise Exception("Back-end denied login request")

        access_token = json.loads(response.text)["access_token"]

        try:
            if client.connected:
                client.disconnect()

            client.connect(
                conf['Url'],
                namespaces=[conf['Namespace']],
                headers={"Authorization": "Bearer " + access_token},
                wait=True
            )
        except Exception as error:
            client.handlers['/']['error'](error)


def load():
    connect()
