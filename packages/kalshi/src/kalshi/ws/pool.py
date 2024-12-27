import asyncio
import random
import time
from collections import defaultdict, deque
from typing import Dict

from common.state import State
from kalshi.authentication import Authenticator
from kalshi.ws.factory import websocket_factory
from loguru import logger
from websockets import WebSocketClientProtocol


class WsPool:
    DEQUE_MAXLEN = 10  # 10 is arbitrary and we may need more depending on latency reqs
    PING_INTERVAL = 10.0  # Per the docs
    RECONNECT_DELAY = 5.0
    WARMUP_TIME_SECS = 100

    def __init__(self, state: State, n_connections: int = 3) -> None:
        self.connection: WebSocketClientProtocol | None = None
        self.connections: Dict[int, WebSocketClientProtocol] = {}
        self.latencies: Dict[int, deque] = {}
        self.usage_counts: Dict[int, int] = defaultdict(int)
        self.state = state
        self.auth = Authenticator(state=self.state)
        self.n_connections = n_connections
        self.next_id = 1  # Counter for the next available ID

    async def _initialize_dummy_connection(self):
        """Initialize and close a dummy connection to warm up resources."""
        logger.info("Initializing dummy connection to warm up resources...")
        dummy_connection = await websocket_factory(
            self.state.ws_uri, extra_headers=self.auth.get_auth_headers_ws()
        )
        await dummy_connection.close()
        logger.info("Dummy connection initialized and closed.")

    async def _create_connections_(self):
        await self._initialize_dummy_connection()  # Warm up resources

        tasks = [
            websocket_factory(
                self.state.ws_uri, extra_headers=self.auth.get_auth_headers_ws()
            )
            for _ in range(self.n_connections)
        ]
        connections = await asyncio.gather(*tasks)

        # Randomize connection IDs to remove ordering bias
        connection_ids = list(range(1, self.n_connections + 1))
        random.shuffle(connection_ids)

        self.connections = {
            conn_id: conn for conn_id, conn in zip(connection_ids, connections)
        }
        for conn_id in self.connections:
            self.latencies[conn_id] = deque(maxlen=self.DEQUE_MAXLEN)
            logger.info(f"Randomized Connection {conn_id} created")

    async def _reconnect_connection_(self, connection_id: int):
        connection = self.connections[connection_id]
        await connection.close()
        logger.info(
            f"Reconnecting to {connection.remote_address} (ID: {connection_id})..."
        )

        while True:
            try:
                new_connection = await websocket_factory(
                    self.state.ws_uri, extra_headers=self.auth.get_auth_headers_ws()
                )
                self.connections[connection_id] = new_connection
                self.latencies[connection_id] = deque(maxlen=self.DEQUE_MAXLEN)
                logger.success(
                    f"Reconnection successful to {new_connection.remote_address} (ID: {connection_id})"
                )
                break
            except Exception as e:
                logger.error(
                    f"Reconnection failed: {e}, retrying in {self.RECONNECT_DELAY}s..."
                )
                await asyncio.sleep(self.RECONNECT_DELAY)

    async def _ping_connection_(self, connection_id: int):
        connection = self.connections[connection_id]
        self.usage_counts[connection_id] += 1  # Track usage count
        start_time = time.perf_counter()
        await connection.ping()
        end_time = time.perf_counter()
        latency = end_time - start_time
        self.latencies[connection_id].append(latency)
        logger.info(f"Connection {connection_id}, Latency={latency:.6f} seconds")

    async def _measure_all_pings_(self):
        start_times = {
            conn_id: time.perf_counter() for conn_id in self.connections.keys()
        }
        tasks = [self._ping_connection_(conn_id) for conn_id in self.connections.keys()]
        await asyncio.gather(*tasks)
        latencies = {
            conn_id: time.perf_counter() - start_times[conn_id]
            for conn_id in self.connections.keys()
        }
        logger.info(f"Simultaneous Ping Latencies: {latencies}")

    async def monitor(self):
        async def ping_task(connection_id: int):
            await asyncio.sleep(1)  # Allow stabilization before the first ping
            while True:
                try:
                    await self._ping_connection_(connection_id)
                except Exception as e:
                    logger.error(f"Error pinging connection {connection_id}: {e}")
                    await self._reconnect_connection_(connection_id)
                await asyncio.sleep(self.PING_INTERVAL)

        # Create a separate task for each connection to ensure independent ping measurements
        tasks = [
            asyncio.create_task(ping_task(connection_id))
            for connection_id in self.connections.keys()
        ]
        await asyncio.gather(*tasks)

    async def run(self):
        await self._create_connections_()
        asyncio.create_task(self.monitor())

        # Wait for a short period to allow initial pings to complete
        await asyncio.sleep(self.WARMUP_TIME_SECS)

        # Set self.connection to the connection with the minimum latency
        min_latency_connection_id = min(
            self.latencies,
            key=lambda conn_id: sum(self.latencies[conn_id])
            / len(self.latencies[conn_id])
            if self.latencies[conn_id]
            else float("inf"),
        )
        self.connection = self.connections[min_latency_connection_id]
        logger.info(
            f"Selected connection with minimum latency: {min_latency_connection_id}"
        )

        # Log usage counts for analysis
        logger.info(f"Connection Usage Counts: {dict(self.usage_counts)}")
