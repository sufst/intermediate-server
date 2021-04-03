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
from socketio import AsyncClient
import asyncio

__all__ = ["socket_io"]


class SocketIO:
    periodic_namespace_emitters = []

    sio_cloud = AsyncClient()
    sio_sufst_vm = AsyncClient()

    async def start(self):
        print("Starting socket.io")
        await self._connect_clients()

        for emitter in self.periodic_namespace_emitters:
            asyncio.get_running_loop().create_task(self._periodic_emitter_task(emitter))

        print("Started socket.io")

    async def _connect_clients(self):
        servers = ["cloud", "sufst_vm"]
        clients = {"cloud": self.sio_cloud, "sufst_vm": self.sio_sufst_vm}

        for server in servers:
            namespaces = []

            for namespace, conf in config.socket_io[server]["namespaces"].items():
                if conf["enable"]:
                    namespaces.append(f"/{namespace}")

            if len(namespaces) > 0:
                await clients[server].connect(config.socket_io[server]["url"], namespaces=namespaces)

    @staticmethod
    async def _periodic_emitter_task(emitter):
        func, interval = emitter

        while True:
            await asyncio.sleep(interval)
            await func()

    def periodic_emitter(self, server, namespace):
        def wrapper(func):
            if config.socket_io[server]["namespaces"][namespace]["enable"]:
                self.periodic_namespace_emitters.append((
                    func,
                    config.socket_io[server]["namespaces"][namespace]["interval"]
                ))
        return wrapper

    @property
    def cloud(self):
        return self.sio_cloud

    @property
    def sufst_vm(self):
        return self.sio_sufst_vm


socket_io = SocketIO()
