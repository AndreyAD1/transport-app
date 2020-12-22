import json

import trio
from trio_websocket import serve_websocket, ConnectionClosed

response_draft = {
    "msgType": "Buses",
    "buses": [
        {"busId": "c790сс", "lat": 55.7500, "lng": 37.600, "route": "120"},
        {"busId": "a134aa", "lat": 55.7494, "lng": 37.621, "route": "670к"},
    ]
}


async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            await ws.send_message(json.dumps(response_draft))
        except ConnectionClosed:
            break


async def main():
    await serve_websocket(echo_server, '127.0.0.1', 8000, ssl_context=None)


trio.run(main)
