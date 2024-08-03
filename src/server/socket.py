"""
WebSocket Server Module

This module sets up a WebSocket server to handle client connections,
receive messages, and send notifications to clients. It also manages
a list of connected clients and saves pending downloads for clients
that are not currently connected.

Functions:
    notify_client(client_id, message): Notify a client with a message if the
    client is connected. If the client is not connected, save the download
    pending information. websocket_handler(websocket, path): Handle incoming
    WebSocket connections and messages. start_websocket_server(): Start the
    WebSocket server on localhost at port 8765.
"""

import json
import asyncio
import websockets
from src.database.db_operations import save_download_pending, delete_all_download_pending  # noqa
from src.logs.logger import LOGGER
from src.config.config import SOCKET_PORT, IP_SERVER

# Socket
connected_clients = {}


async def notify_client(client_id, message):
    """
    Notify a client with a message if the client is connected.
    If the client is not connected, save the download pending information.

    Args:
        client_id (str): The ID of the client to notify.
        message (dict): The message to send to the client.

    """
    if client_id in connected_clients:
        websocket = connected_clients[client_id]
        await websocket.send(json.dumps(message))
        delete_all_download_pending(client_id)
    else:
        save_download_pending(client_id, message["zip_path"], True)


async def websocket_handler(websocket, path):
    """
    Handle incoming WebSocket connections and messages.

    Args:
        websocket (websockets.WebSocketServerProtocol): The WebSocket
        connection. path (str): The path of the WebSocket connection.

    """
    client_id = path.strip("/")
    connected_clients[client_id] = websocket
    try:
        async for message in websocket:
            LOGGER.info('Received message: %s', message)
    except websockets.exceptions.ConnectionClosed as e:
        LOGGER.error('Connection closed: %s', e)
    finally:
        if client_id in connected_clients:
            del connected_clients[client_id]


def start_websocket_server():
    """
    Start the WebSocket server on IP_SERVER at port SOCKET_PORT.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(
        websocket_handler, IP_SERVER, int(SOCKET_PORT))
    loop.run_until_complete(start_server)
    loop.run_forever()
