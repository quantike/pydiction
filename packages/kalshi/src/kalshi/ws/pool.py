import asyncio
from collections import deque
import time
from typing import Dict
from common.state import State
from loguru import logger
from websockets import WebSocketClientProtocol

from kalshi.authentication import Authenticator
from kalshi.ws.factory import websocket_factory

class WsPool:
    DEQUE_MAXLEN = 10  # 10 is arbitrary and we may need more depending on latency reqs
    PING_INTERVAL = 10.0  # Per the docs
    RECONNECT_DELAY = 5.0
    WARMUP_TIME_SECS = 100

    def __init__(self, state: State, n_connections: int = 3) -> None:
        self.connection: WebSocketClientProtocol | None = None
        self.connections: Dict[int, WebSocketClientProtocol] = {}
        self.latencies: Dict[int, deque] = {}
        self.state = state
        self.auth = Authenticator(state=self.state)
        self.n_connections = n_connections
        self.next_id = 1  # Counter for the next available ID

    async def _create_connections_(self):
        for _ in range(self.n_connections):
            connection = await websocket_factory(self.state.ws_uri, extra_headers=self.auth.get_auth_headers_ws())
            connection_id = self.next_id
            self.next_id += 1
            self.connections[connection_id] = connection
            self.latencies[connection_id] = deque(maxlen=self.DEQUE_MAXLEN)
            logger.info(f"Created connection {connection_id} to {connection.remote_address}")

    async def _reconnect_connection_(self, connection_id: int):
        connection = self.connections[connection_id]
        await connection.close()
        logger.info(f"Reconnecting to {connection.remote_address} (ID: {connection_id})...")

        while True:
            try:
                new_connection = await websocket_factory(self.state.ws_uri, extra_headers=self.auth.get_auth_headers_ws())
                self.connections[connection_id] = new_connection
                self.latencies[connection_id] = deque(maxlen=self.DEQUE_MAXLEN)
                logger.success(f"Reconnection successful to {new_connection.remote_address} (ID: {connection_id})")
                break
            except Exception as e:
                logger.error(f"Reconnection failed: {e}, retrying in {self.RECONNECT_DELAY}s...")
                await asyncio.sleep(self.RECONNECT_DELAY)

    async def _ping_connection_(self, connection_id: int):
        connection = self.connections[connection_id]
        start_time = time.time()
        await connection.ping()
        end_time = time.time()
        latency = end_time - start_time
        self.latencies[connection_id].append(latency)
        logger.info(f"Connection {connection_id}, Latency={latency}")

    async def monitor(self):
        while True:
            for connection_id in list(self.connections.keys()):
                try:
                    await self._ping_connection_(connection_id)
                except Exception as e:
                    logger.error(f"Error pinging connection {connection_id}: {e}")
                    await self._reconnect_connection_(connection_id)

            await asyncio.sleep(self.PING_INTERVAL)

    async def run(self):
        await self._create_connections_()
        asyncio.create_task(self.monitor())

        # Wait for a short period to allow initial pings to complete
        await asyncio.sleep(self.WARMUP_TIME_SECS)

        # Set self.connection to the connection with the minimum latency
        min_latency_connection_id = min(self.latencies, key=lambda conn_id: sum(self.latencies[conn_id]) / len(self.latencies[conn_id]) if self.latencies[conn_id] else float('inf'))
        self.connection = self.connections[min_latency_connection_id]
        logger.info(f"Selected connection with minimum latency: {min_latency_connection_id}")

