from itertools import cycle, islice
import json
import logging
import os
import random

import click
import trio
from trio_websocket import open_websocket_url, ConnectionClosed, HandshakeError

logger = logging.getLogger(__file__)


def relaunch_on_disconnect(async_function):
    async def wrapper(*args, **kwargs):
        while True:
            try:
                logger.warning(f'Launch {async_function.__name__}')
                await async_function(*args, **kwargs)
            except ConnectionClosed:
                logger.warning('Connection closed. Trying to reconnect.')
            except HandshakeError:
                logger.warning('No connection. Trying to establish it.')

            await trio.sleep(1)
    return wrapper


def load_routes(route_number, directory_path='routes'):
    for filename in islice(os.listdir(directory_path), route_number):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def generate_bus_id(route_id, bus_index):
    return f'{route_id}-{bus_index}'


async def run_bus(send_channel, bus_id, bus_coordinates, route_name, timeout):
    for latitude, longitude in cycle(bus_coordinates):
        await send_channel.send((bus_id, latitude, longitude, route_name))
        await trio.sleep(timeout)


@relaunch_on_disconnect
async def send_updates(url, receive_channel):
    try:
        async with open_websocket_url(url) as ws:
            logger.debug('Connect to a server')
            async for bus_id, latitude, longitude, name in receive_channel:
                bus_info = {
                    'busId': bus_id,
                    'lat': latitude,
                    'lng': longitude,
                    'route': name
                }
                try:
                    json_message = json.dumps(bus_info, ensure_ascii=False)
                    await ws.send_message(json_message)
                    logger.debug(f'Send message {bus_info}')
                except ConnectionClosed as ex:
                    logger.warning(f'Connection closed: {url}')
                    raise ex
    except HandshakeError as ex:
        logger.error(f'Can not establish connection with {url}')
        raise ex


async def run_buses(
        server_url,
        route_number,
        buses_per_route,
        socket_number,
        emulator_id,
        refresh_timeout
):
    async with trio.open_nursery() as nursery:
        channels = [trio.open_memory_channel(0) for _ in range(socket_number)]
        for route in load_routes(route_number):
            for bus_index in range(buses_per_route):
                bus_id = generate_bus_id(route['name'], bus_index)
                bus_id = emulator_id + bus_id
                random_index = random.randrange(0, len(route['coordinates']))
                bus_coordinates = [
                    *route['coordinates'][random_index:],
                    *route['coordinates'][:random_index]
                ]
                send_channel, _ = random.choice(channels)
                nursery.start_soon(
                    run_bus,
                    send_channel,
                    bus_id,
                    bus_coordinates,
                    route['name'],
                    refresh_timeout
                )

        for send_channel, receive_channel in channels:
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
@click.option(
    '--emulator_id',
    default='',
    help='This string will be the prefix of every bus id.'
)
@click.option(
    '--refresh_timeout',
    default=1,
    type=click.IntRange(1),
    help='The timeout to update bus coordinates (seconds).'
)
@click.option(
    '-v',
    '--verbose',
    is_flag=True,
    type=click.BOOL,
    help='Output detailed log messages.'
)
def main(
        server_url,
        route_number,
        buses_per_route,
        websocket_number,
        emulator_id,
        refresh_timeout,
        verbose
):
    """Send bus coordinates to a server."""
    logging.basicConfig(level=logging.ERROR)
    logger.setLevel(logging.ERROR)
    if verbose:
        logger.setLevel(logging.DEBUG)
    trio.run(
        run_buses,
        server_url,
        route_number,
        buses_per_route,
        websocket_number,
        emulator_id,
        refresh_timeout
    )


if __name__ == '__main__':
    main()
