import itertools
import json

import trio
from trio_websocket import serve_websocket, ConnectionClosed

response = {
    'msgType': 'Buses',
}
with open('156.json', 'r') as bus_path_file:
    bus_features = json.load(bus_path_file)

route_name = bus_features['name'] 
bus_coordinates = bus_features['coordinates']


async def fake_bus(request):
    ws = await request.accept()
    for latitude, longitude in itertools.cycle(bus_coordinates):
        try:
            # message = await ws.get_message()
            response['buses'] = [
                {
                    'busId': 1,
                    'lat': latitude, 
                    'lng': longitude, 
                    'route': route_name
                }
            ]
            await ws.send_message(json.dumps(response))
        except ConnectionClosed:
            break
        await trio.sleep(1)


async def main():
    await serve_websocket(fake_bus, '127.0.0.1', 8000, ssl_context=None)


trio.run(main)
