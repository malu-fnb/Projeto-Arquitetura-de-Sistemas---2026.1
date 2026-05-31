from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

from parser import ParserError, parse_message, to_json_string
from handlers.temperatura import processar_temperatura
from handlers.pressao import processar_pressao
from handlers.umidade import processar_umidade
from handlers.luminosidade import processar_luminosidade
from clients.dashboard_client import DashboardClient

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IoT middleware MQTT client and message parser")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "mosquitto"), help="MQTT broker host")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")), help="MQTT broker port")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password")
    parser.add_argument("--client-id", default=os.getenv("MQTT_CLIENT_ID"), help="MQTT client id")

    subcommands = parser.add_subparsers(dest="command")

    listen = subcommands.add_parser("listen", help="Connect to the broker and receive messages")
    listen.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "sensores/#"), help="Topic to subscribe")
    listen.add_argument("--qos", type=int, default=0, choices=[0, 1, 2], help="MQTT QoS")
    listen.add_argument(
        "--format",
        default=os.getenv("PARSER_FORMAT", "auto"),
        choices=["auto", "csv", "text", "json", "binary"],
        help="How received payloads should be parsed",
    )

    publish = subcommands.add_parser("publish", help="Connect to the broker and publish one message")
    publish.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "sensores/temperatura"), help="Topic to publish")
    publish.add_argument("--qos", type=int, default=0, choices=[0, 1, 2], help="MQTT QoS")
    publish.add_argument("--retain", action="store_true", help="Publish with retain flag")
    publish.add_argument("--payload", help="Text payload to publish")
    publish.add_argument("--file", type=Path, help="File whose bytes will be published")

    parse = subcommands.add_parser("parse", help="Parse a local payload without using MQTT")
    parse.add_argument(
        "--format",
        default="auto",
        choices=["auto", "csv", "text", "json", "binary"],
        help="Payload format",
    )
    parse.add_argument("--payload", help="Text payload to parse")
    parse.add_argument("--file", type=Path, help="File whose bytes will be parsed")

    return parser


def read_payload(payload: Optional[str], file_path: Optional[Path]) -> bytes:
    if payload is not None and file_path is not None:
        raise ValueError("Use only one input source: --payload or --file.")

    if file_path is not None:
        return file_path.read_bytes()

    if payload is not None:
        return payload.encode("utf-8")

    raise ValueError("You must provide --payload or --file.")


def create_mqtt_client(args: argparse.Namespace):
    from mqtt_client import MQTTClient

    return MQTTClient(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        username=args.username,
        password=args.password,
    )


def create_dashboard_client() -> DashboardClient:
    return DashboardClient(
        base_url=os.getenv("DASHBOARD_URL", "http://dashboard:5000"),
        username=os.getenv("DASHBOARD_USERNAME", "admin"),
        password=os.getenv("DASHBOARD_PASSWORD", "admin123"),
    )


def process_sensor_data(parsed_data, correlation_id):
    sensor_data = parsed_data.get("data", {})
    sensor_type = sensor_data.get("sensor")

    if sensor_type == "temperatura":
        return processar_temperatura(sensor_data, correlation_id)

    if sensor_type == "umidade":
        return processar_umidade(sensor_data, correlation_id)

    if sensor_type == "pressao":
        return processar_pressao(sensor_data, correlation_id)

    if sensor_type == "luminosidade":
        return processar_luminosidade(sensor_data, correlation_id)

    raise ValueError(f"Sensor desconhecido: {sensor_type}")


def build_dashboard_payload(topic: str, processed: dict) -> dict:
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device_id": processed.get("sensor", "desconhecido"),
        "topic": topic,
        "payload": processed,
    }


def handle_listen(args: argparse.Namespace) -> None:
    client = create_mqtt_client(args)

    dashboard_client = create_dashboard_client()
    dashboard_available = dashboard_client.login()

    if not dashboard_available:
        logging.warning("Dashboard indisponível ou login falhou. Middleware continuará apenas processando logs.")

    client.connect()

    def on_message(topic: str, payload: bytes, qos: int, retain: bool) -> None:
        correlation_id = str(uuid4())

        try:
            parsed = parse_message(payload, args.format)
            processed = process_sensor_data(parsed, correlation_id)

            output = {
                "topic": topic,
                "qos": qos,
                "retain": retain,
                "correlation_id": correlation_id,
                "message": processed,
            }

            print(to_json_string(output), flush=True)

            dashboard_payload = build_dashboard_payload(topic, processed)

            if dashboard_available:
                sent = dashboard_client.send_data(dashboard_payload)

                if not sent:
                    logging.error(
                        {
                            "erro": "Falha ao enviar dado para o dashboard",
                            "topic": topic,
                            "correlation_id": correlation_id,
                        }
                    )

        except ParserError as exc:
            logging.error(
                {
                    "erro": "Falha ao fazer parse da mensagem",
                    "topic": topic,
                    "correlation_id": correlation_id,
                    "detalhes": str(exc),
                }
            )

        except Exception as exc:
            logging.error(
                {
                    "erro": "Falha ao processar sensor",
                    "topic": topic,
                    "correlation_id": correlation_id,
                    "detalhes": str(exc),
                }
            )

    client.subscribe(args.topic, on_message, qos=args.qos)
    logging.info("Listening on topic '%s'. Press Ctrl+C to stop.", args.topic)
    client.listen_forever()


def handle_publish(args: argparse.Namespace) -> None:
    payload = read_payload(args.payload, args.file)
    client = create_mqtt_client(args)

    try:
        client.connect()
        client.publish(args.topic, payload, qos=args.qos, retain=args.retain)
    finally:
        client.disconnect()


def handle_parse(args: argparse.Namespace) -> None:
    payload = read_payload(args.payload, args.file)
    parsed = parse_message(payload, args.format)
    print(to_json_string(parsed))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    cli = build_parser()
    args = cli.parse_args()

    if args.command is None:
        args = cli.parse_args(["listen"])

    try:
        if args.command == "listen":
            handle_listen(args)
        elif args.command == "publish":
            handle_publish(args)
        elif args.command == "parse":
            handle_parse(args)
        else:
            cli.print_help()
            return 1
    except (OSError, ParserError, ValueError) as exc:
        logging.error("%s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())