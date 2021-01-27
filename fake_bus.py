from itertools import cycle, islice
import json
import os
import random
from sys import stderr

import click
import trio
from trio_websocket import open_websocket_url, ConnectionClosed


def load_routes(route_number, directory_path='routes'):
    for filename in islice(os.listdir(directory_path), route_number):
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


async def run_buses(server_url, route_number, buses_per_route, ws_number):
    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel(0)
        for route in load_routes(route_number):
            for bus_index in range(buses_per_route):
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
        for _ in range(ws_number):
            nursery.start_soon(send_updates, server_url, receive_channel)


@click.command()
@click.argument('server_url')
@click.option(
    '--route_number',
    required=True,
    type=click.IntRange(1),
    help='The number of bus routes.'
)
@click.option(
    '--buses_per_route',
    required=True,
    type=click.IntRange(1),
    help='The number of buses per route.'
)
@click.option(
    '--websocket_number',
    default=1,
    type=click.IntRange(1),
    help='The number of open websockets.'
)
def main(server_url, route_number, buses_per_route, websocket_number):
    """Send bus coordinates to a server."""
    trio.run(
        run_buses,
        server_url,
        route_number,
        buses_per_route,
        websocket_number
    )


if __name__ == '__main__':
    main()
