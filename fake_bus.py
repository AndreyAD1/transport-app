import itertools
import json
from sys import stderr

import trio
from trio_websocket import open_websocket_url, ConnectionClosed

with open('156.json', 'r') as bus_path_file:
    bus_features = json.load(bus_path_file)

route_name = bus_features['name'] 
bus_coordinates = bus_features['coordinates']


async def main():
    try:
        async with open_websocket_url('ws://127.0.0.1:8080') as ws:
            for latitude, longitude in itertools.cycle(bus_coordinates):
                try:
                    response = {
                        'busId': '156-0',
                        'lat': latitude,
                        'lng': longitude,
                        'route': route_name
                    }
                    await ws.send_message(json.dumps(response))
                except ConnectionClosed:
                    break
                await trio.sleep(1)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


trio.run(main)
