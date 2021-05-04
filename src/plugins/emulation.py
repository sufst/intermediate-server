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
from src.helpers import config, scheduler
from time import time
import functools


class _Modules:
    def __init__(self, modules):
        self.__dict__ = modules


_consumers = []
_x = 0
_conf = config.config['emulation']


def _invoke_consumers():
    global _x
    data = {}
    mods = {}

    for module in _conf['Modules'].split(' '):
        mods[module] = __import__(module)

    mods = _Modules(mods)
    now = round(time(), 3)

    for sensor, conf in config.sensors.items():
        data[sensor] = {
            "value": (lambda modules, x: eval(conf["emulation"]))(mods, _x),
            "epoch": now
        }
    _x += 1

    for consumer in _consumers:
        consumer(data)


def on(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        func(*args, **kwargs)

    _consumers.append(decorator)
    return decorator


def load():
    if _conf.getboolean('Enable'):
        scheduler.add_job(_invoke_consumers, scheduler.IntervalTrigger(seconds=_conf.getfloat('Interval')))
