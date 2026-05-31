"""MQTT client abstraction used by the middleware.

Supported functions required by issue #1:
- Connect to the broker
- Publish messages
- Receive messages from subscribed topics
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Callable, Optional, Union
from uuid import uuid4

import paho.mqtt.client as mqtt

MessagePayload = Union[str, bytes, bytearray, dict, list]
MessageHandler = Callable[[str, bytes, int, bool], None]

LOGGER = logging.getLogger(__name__)


class MQTTClientError(RuntimeError):
    """Raised when the MQTT client cannot complete an operation."""


class MQTTClient:
    """Small wrapper around paho-mqtt with explicit middleware operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: int = 60,
    ) -> None:
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.client_id = client_id or f"middleware-{uuid4().hex[:8]}"
        self._connected = threading.Event()
        self._message_handler: Optional[MessageHandler] = None

        self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
        if username:
            self.client.username_pw_set(username=username, password=password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    @classmethod
    def from_environment(cls) -> "MQTTClient":
        """Create a client using environment variables used by docker-compose."""
        return cls(
            host=os.getenv("MQTT_HOST", "localhost"),
            port=int(os.getenv("MQTT_PORT", "1883")),
            client_id=os.getenv("MQTT_CLIENT_ID"),
            username=os.getenv("MQTT_USERNAME") or None,
            password=os.getenv("MQTT_PASSWORD") or None,
            keepalive=int(os.getenv("MQTT_KEEPALIVE", "60")),
        )

    def connect(self, timeout: int = 10, retries: int = 5, retry_delay: float = 2.0) -> None:
        """Connect to the MQTT broker and start the network loop."""
        last_error: Optional[BaseException] = None

        for attempt in range(1, retries + 1):
            try:
                LOGGER.info(
                    "Connecting to MQTT broker %s:%s with client_id=%s (attempt %s/%s)",
                    self.host,
                    self.port,
                    self.client_id,
                    attempt,
                    retries,
                )
                self.client.connect(self.host, self.port, self.keepalive)
                self.client.loop_start()

                if self._connected.wait(timeout=timeout):
                    LOGGER.info("Connected to MQTT broker %s:%s", self.host, self.port)
                    return

                last_error = TimeoutError("Connection timeout waiting for CONNACK.")
                self.client.loop_stop()
                self.client.disconnect()
            except BaseException as exc:  # noqa: BLE001 - keep retry reason
                last_error = exc
                LOGGER.warning("MQTT connection attempt failed: %s", exc)

            if attempt < retries:
                time.sleep(retry_delay)

        raise MQTTClientError(f"Could not connect to MQTT broker: {last_error}")

    def disconnect(self) -> None:
        """Disconnect from the broker and stop the network loop."""
        self.client.disconnect()
        self.client.loop_stop()
        self._connected.clear()

    def publish(
        self,
        topic: str,
        payload: MessagePayload,
        qos: int = 0,
        retain: bool = False,
        timeout: int = 10,
    ) -> None:
        """Publish a message to a topic."""
        if not topic:
            raise MQTTClientError("Topic cannot be empty.")

        encoded_payload = self._encode_payload(payload)
        result = self.client.publish(topic, encoded_payload, qos=qos, retain=retain)
        completed = result.wait_for_publish(timeout=timeout)

        if not completed or result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise MQTTClientError(f"Failed to publish to topic '{topic}'. MQTT rc={result.rc}")

        LOGGER.info("Published %s bytes to topic %s", len(encoded_payload), topic)

    def subscribe(self, topic: str, handler: MessageHandler, qos: int = 0) -> None:
        """Subscribe to a topic and register a receive callback."""
        if not topic:
            raise MQTTClientError("Topic cannot be empty.")

        self._message_handler = handler
        result, mid = self.client.subscribe(topic, qos=qos)
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise MQTTClientError(f"Failed to subscribe to topic '{topic}'. MQTT rc={result}")

        LOGGER.info("Subscribed to topic %s with mid=%s", topic, mid)

    def listen_forever(self) -> None:
        """Keep the process alive while MQTT callbacks receive messages."""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            LOGGER.info("Stopping MQTT listener.")
        finally:
            self.disconnect()

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        if rc == mqtt.CONNACK_ACCEPTED:
            self._connected.set()
            return

        LOGGER.error("MQTT broker refused connection. rc=%s", rc)
        self._connected.clear()

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        self._connected.clear()
        if rc != mqtt.MQTT_ERR_SUCCESS:
            LOGGER.warning("Unexpected MQTT disconnect. rc=%s", rc)

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        if self._message_handler:
            self._message_handler(
                message.topic,
                bytes(message.payload),
                int(message.qos),
                bool(message.retain),
            )

    @staticmethod
    def _encode_payload(payload: MessagePayload) -> bytes:
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, bytearray):
            return bytes(payload)
        if isinstance(payload, str):
            return payload.encode("utf-8")
        if isinstance(payload, (dict, list)):
            return json.dumps(payload, ensure_ascii=False).encode("utf-8")

        raise MQTTClientError(f"Unsupported payload type: {type(payload).__name__}")