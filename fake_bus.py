import itertools
import json
import os
from sys import stderr

import trio
from trio_websocket import open_websocket_url, ConnectionClosed


async def run_bus(url, bus_id, route):
    try:
        async with open_websocket_url(url) as ws:
            for latitude, longitude in itertools.cycle(route):
                try:
                    response = {
                        'busId': bus_id,
                        'lat': latitude,
                        'lng': longitude,
                        'route': bus_id
                    }
                    await ws.send_message(json.dumps(response, ensure_ascii=False))
                except ConnectionClosed:
                    break
                await trio.sleep(1)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


async def main():
    async with trio.open_nursery() as nursery:
        for route in load_routes():
            route_name = route['name']
            bus_coordinates = route['coordinates']
            nursery.start_soon(
                run_bus,
                'ws://127.0.0.1:8080',
                route_name,
                bus_coordinates
            )


if __name__ == '__main__':
    trio.run(main)
