from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from parser import ParserError, parse_message, to_json_string
from handlers.temperatura import processar_temperatura
from handlers.pressao import processar_pressao
from handlers.umidade import processar_umidade
from handlers.luminosidade import processar_luminosidade

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IoT middleware MQTT client and message parser")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"), help="MQTT broker host")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")), help="MQTT broker port")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password")
    parser.add_argument("--client-id", default=os.getenv("MQTT_CLIENT_ID"), help="MQTT client id")

    subcommands = parser.add_subparsers(dest="command")

    listen = subcommands.add_parser("listen", help="Connect to the broker and receive messages")
    listen.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "middleware/input"), help="Topic to subscribe")
    listen.add_argument("--qos", type=int, default=0, choices=[0, 1, 2], help="MQTT QoS")
    listen.add_argument(
        "--format",
        default=os.getenv("PARSER_FORMAT", "auto"),
        choices=["auto", "csv", "text", "json", "binary"],
        help="How received payloads should be parsed",
    )

    publish = subcommands.add_parser("publish", help="Connect to the broker and publish one message")
    publish.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "middleware/input"), help="Topic to publish")
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


def handle_listen(args: argparse.Namespace) -> None:
    client = create_mqtt_client(args)
    client.connect()

    def on_message(topic: str, payload: bytes, qos: int, retain: bool) -> None:
        try:
            parsed = parse_message(payload, args.format)
            output = {
                "topic": topic,
                "qos": qos,
                "retain": retain,
                "message": parsed,
            }
            print(to_json_string(output), flush=True)
        except ParserError as exc:
            logging.error("Could not parse message received on %s: %s", topic, exc)

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