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
from socketio import Client, ClientNamespace
from emulation import emulator
import requests
import json
from scheduler import scheduler, IntervalTrigger, DateTrigger
from protocol import protocol
from time import sleep
import functools

__all__ = ["socket_io"]


class SocketIO:
    clients = {
        "cloud": Client(reconnection=False),
        "sufst_vm": Client(reconnection=False)
    }
    health_job = None
    restart_job = None
    event_handlers = {}

    def on(self, event):
        def wrapper(func):
            @functools.wraps(func)
            def decorator(*args, **kwargs):
                func(*args, **kwargs)

            self.event_handlers[event] = decorator
            return decorator

        return wrapper

    def _health_check(self):
        healthy = False

        for _, client in self.clients.items():
            if client.connected:
                healthy = True

        if not healthy:
            self._unhealthy("Health check failed")

    def _unhealthy(self, error):
        if self.health_job is not None:
            self.health_job.remove()
            del self.health_job

        if self.event_handlers["error"] is not None:
            self.event_handlers["error"](error)

    def start(self):
        print("Starting socket.io")

        scheduler.add_job(self._connect_clients)

        print("Started socket.io")

    def _connect_clients(self):
        connected = False

        for server, client in self.clients.items():
            try:
                self._connect_client(client, server)
            except Exception as error:
                print(error)
            else:
                connected = True

        if not connected:
            self._unhealthy(ConnectionError("No active clients"))
        else:
            self.health_job = scheduler.add_job(self._health_check, IntervalTrigger(seconds=1))

    @staticmethod
    def _connect_client(client, server):
        namespace = config.socket_io[server]["namespace"]
        url = config.socket_io[server]['url']

        client.register_namespace(_Namespace(namespace, server))

        try:
            print(f"Attempting {url}/login")
            response = requests.post(
                f"{url}/login",
                headers={"Content-Type": "application/json"},
                data=json.dumps({
                    "username": "intermediate-server",
                    "password": "sufst"
                }), timeout=10)
        except Exception as error:
            print(error)
        else:
            if response.status_code != 200:
                raise Exception("Back-end denied login request")

            access_token = json.loads(response.text)["access_token"]

            try:
                if client.connected:
                    client.disconnect()

                client.connect(
                    config.socket_io[server]["url"],
                    namespaces=[namespace],
                    headers={"Authorization": "Bearer " + access_token},
                    wait=True
                )
            except Exception as error:
                raise error

    @property
    def cloud(self):
        return self.clients["cloud"]

    @property
    def sufst_vm(self):
        return self.clients["sufst_vm"]


class _Namespace(ClientNamespace):
    datastore = {}
    server = None
    job = None

    def __init__(self, namespace, server):
        super().__init__(namespace)
        self.datastore = {}
        self.server = server
        self.job = None

        if not config.socket_io[server]["emulation"]:
            for pdu in config.schema["pdu"]:
                protocol.register_on(pdu, self._handle_protocol_pdu)

    def _handle_protocol_pdu(self, pdu):
        for sensor, value in filter(lambda entry: entry[0] != "epoch", pdu.items()):
            self._add_sensor_values_to_datastore(sensor, {"epoch": pdu["epoch"], "value": value})

    def _emit_datastore(self):
        if not self.datastore == {}:
            try:
                self.emit("data", json.dumps(self.datastore))
            except Exception as error:
                print(repr(error))
                print("Stopping emit job")
                self.job.remove()

            self.datastore = {}

    def _add_sensor_values_to_datastore(self, sensor, values):
        if sensor not in self.datastore:
            self.datastore[sensor] = []
        self.datastore[sensor].append(values)

    def _emulation_consumer(self, data):
        for sensor, values in data.items():
            self._add_sensor_values_to_datastore(sensor, values)

    def on_connect(self):
        print(f"{self.server} <- {self.namespace}")
        print("Starting emit job")
        self.job = scheduler.add_job(
            self._emit_datastore, IntervalTrigger(seconds=config.socket_io[self.server]["interval"]))
        self.emit("meta", json.dumps(config.sensors))

        if config.socket_io[self.server]["emulation"]:
            emulator.register_consumer(self._emulation_consumer)

    def on_disconnect(self):
        print(f"{self.server} </- {self.namespace}")


socket_io = SocketIO()
