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
from dotenv.main import load_dotenv

from src.helpers import config, scheduler
from src.plugins import schema, sio, emulation, plugins_load, plugins_run
import asyncio
from datetime import datetime
from time import time
import json
import os

_datastore = {}


@schema.on('connect')
def _on_schema_connect():
    print('schema connected')


@schema.on('disconnect')
def _on_schema_disconnect(exc):
    print('schema disconnect')
    if exc is not None:
        print(f'Schema error: {exc}')


@emulation.on
def _on_emulation(data):
    if sio.client.connected:
        for sensor, values in data.items():
            if sensor not in _datastore:
                _datastore[sensor] = []
            _datastore[sensor].append(values)


@schema.on('PDU')
def _on_schema_pdu(pdu):
    for sensor, value in filter(lambda entry: entry[0] != 'epoch', pdu.items()):
        if sensor not in _datastore:
            _datastore[sensor] = []
        _datastore[sensor].append({'epoch': pdu['epoch'], 'value': value})


@scheduler.schedule_job(scheduler.IntervalTrigger(seconds=sio.conf.getfloat('Interval')))
def on_sio_client_emit():
    if sio.client.connected:
        if not _datastore == {}:
            sio.client.emit('data', json.dumps(_datastore), sio.conf['Namespace'])

    _datastore.clear()


@sio.client.on('connect', namespace=sio.conf['Namespace'])
def on_sio_client_namespace_connect():
    print(f'{sio.conf["Namespace"]} connect')
    sio.client.emit('meta', json.dumps(config.sensors), sio.conf['Namespace'])


@sio.client.on('disconnect', namespace=sio.conf['Namespace'])
def on_sio_client_namespace_connect():
    print(f'{sio.conf["Namespace"]} disconnect')
    wait = sio.conf.getint('RetryInterval')
    print(f'Attempting client restart in {wait}s')

    scheduler.add_job(sio.connect, scheduler.DateTrigger(datetime.fromtimestamp(time() + wait)))


@sio.client.on('error')
def _on_error(err):
    print(err)
    wait = sio.conf.getint('RetryInterval')
    print(f'Attempting client restart in {wait}s')

    scheduler.add_job(sio.connect, scheduler.DateTrigger(datetime.fromtimestamp(time() + wait)))


if __name__ == '__main__':
    print(f'SUFST Intermediate-Server Copyright (C) 2021 Nathan Rowley-Smith\n' +
          'This program comes with ABSOLUTELY NO WARRANTY;\n' +
          'This is free software, and you are welcome to redistribute it')

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    plugins_load()

    plugins_run()

    try:
        loop.run_forever()
    except Exception as error:
        print(repr(error))
        print('Stopping')
        loop.stop()

    print('Stopped')
