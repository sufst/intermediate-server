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
from protocol.pdu import PDU
from configuration import config
import asyncio
from protocol.factory import Socket, XBee
import functools

__all__ = ["protocol"]


class Protocol:
    event_handlers = {}
    pdus = {}

    def init_protocol(self):
        for name, conf in config.schema["pdu"].items():
            self.pdus[conf["id"]] = PDU(name, conf["struct"])

    def start(self):
        print("Starting protocol")

        if config.client["socket"]["enable"]:
            print("Starting protocol socket")
            asyncio.get_event_loop().create_task(
                asyncio.get_event_loop().create_server(
                    lambda: Socket(self),
                    config.client["socket"]["host"],
                    config.client["socket"]["port"])
            )
            print("Protocol socket serving "
                  f"{config.client['socket']['host']}:{config.client['socket']['port']}")
            print("Started protocol socket")
        else:
            print("Starting protocol Xbee")
            XBee(
                config.client["xbee"]["com"],
                config.client["xbee"]["baud"],
                config.client["xbee"]["mac"],
                self
            )
            print("Started protocol XBee")

        print("Started protocol")

    def _parse_data(self, data):
        index = 0
        while index < len(data):
            if data[index] != config.schema["start_byte"]:
                raise Exception("Invalid start byte")
            index += 1

            pdu_type = data[index]
            if pdu_type in self.pdus:
                index += 1
                if self.pdus[pdu_type].length > len(data) - index:
                    raise Exception("Invalid data length")
                else:
                    self.pdus[pdu_type].decode(data[index:index + self.pdus[pdu_type].length])
                    if self.pdus[pdu_type].name in self.event_handlers:
                        self.event_handlers[self.pdus[pdu_type].name](self.pdus[pdu_type].fields)

                    index += self.pdus[pdu_type].length
            else:
                raise Exception("Invalid PDU type")

    def connection_made(self):
        if "connect" in self.event_handlers:
            self.event_handlers["connect"]()

    def data_received(self, data):
        try:
            self._parse_data(data)
        except Exception as error:
            print(error)

    def connection_lost(self, exc):
        if "disconnect" in self.event_handlers:
            self.event_handlers["disconnect"](exc)

    def on(self, event):
        def wrapper(func):
            @functools.wraps(func)
            def decorator(*args, **kwargs):
                func(*args, **kwargs)

            self.event_handlers[event] = decorator

            return decorator

        return wrapper

    def register_on(self, event, func):
        self.event_handlers[event] = func


protocol = Protocol()
