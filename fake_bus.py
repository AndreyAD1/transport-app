from itertools import cycle
import json
import os
import random
from sys import stderr

import trio
from trio_websocket import open_websocket_url, ConnectionClosed

BUS_NUMBER_PER_ROUTE = 35
SERVER_URL = 'ws://127.0.0.1:8080'


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def generate_bus_id(route_id, bus_index):
    return f'{route_id}-{bus_index}'


async def run_bus(send_channel, bus_id, bus_coordinates, route_name):
    for latitude, longitude in cycle(bus_coordinates):
        await send_channel.send((bus_id, latitude, longitude, route_name))


async def send_updates(url, receive_channel):
    try:
        async with open_websocket_url(url) as ws:
            async for bus_id, latitude, longitude, route_name in receive_channel:
                response = {
                    'busId': bus_id,
                    'lat': latitude,
                    'lng': longitude,
                    'route': route_name
                }
                try:
                    await ws.send_message(
                        json.dumps(
                            response,
                            ensure_ascii=False
                        )
                    )
                except ConnectionClosed:
                    break
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


async def main():
    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(0)
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
                    send_channel,
                    bus_id,
                    bus_coordinates,
                    route['name']
                )
        nursery.start_soon(send_updates, SERVER_URL, receive_channel)


if __name__ == '__main__':
    trio.run(main)
