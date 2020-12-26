from itertools import cycle
import json
import os
import random
from sys import stderr

import trio
from trio_websocket import open_websocket_url, ConnectionClosed

BUS_NUMBER_PER_ROUTE = 3


async def run_bus(url, bus_id, route, route_name):
    try:
        async with open_websocket_url(url) as ws:
            for latitude, longitude in cycle(route):
                try:
                    response = {
                        'busId': bus_id,
                        'lat': latitude,
                        'lng': longitude,
                        'route': route_name
                    }
                    await ws.send_message(
                        json.dumps(
                            response,
                            ensure_ascii=False
                        )
                    )
                except ConnectionClosed:
                    break
                await trio.sleep(0.1)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def main():
    async with trio.open_nursery() as nursery:
        for route in load_routes():
            for bus_index in range(BUS_NUMBER_PER_ROUTE):
                bus_id = generate_bus_id(route['name'], bus_index)
                random_index = random.randrange(0, len(route['coordinates']))
                bus_coordinates = [
                    *route['coordinates'][random_index:],
                    *route['coordinates'][:random_index]
                ]
                nursery.start_soon(
                    run_bus,
                    'ws://127.0.0.1:8080',
                    bus_id,
                    bus_coordinates,
                    route['name']
                )


if __name__ == '__main__':
    trio.run(main)
