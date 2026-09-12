"""MQTT publishing with Home Assistant MQTT discovery."""
from __future__ import annotations

import json
import logging

import paho.mqtt.client as mqtt

from .config import Config

log = logging.getLogger(__name__)

# HA MQTT discovery payload schema (homeassistant/sensor/<object_id>/config)
_DISCOVERY = "sensor"
_BINARY_DISCOVERY = "binary_sensor"


def _unique_id(cfg: Config, suffix: str = "") -> str:
    base = cfg.luminance_sensor.object_id if suffix == "luminance" else (cfg.dark_sensor.object_id if cfg.dark_sensor else cfg.luminance_sensor.object_id)
    if suffix:
        return f"luminance_probe_{base}_{suffix}"
    return f"luminance_probe_{base}"


def _discovery_topic(cfg: Config, component: str, object_id: str) -> str:
    return f"{cfg.mqtt.topic}/{component}/{object_id}/config"


def _state_topic(cfg: Config, object_id: str) -> str:
    return f"{cfg.mqtt.topic}/sensor/{object_id}/state"


def publish_luminance(cfg: Config, value: float, client: mqtt.Client) -> None:
    oid = cfg.luminance_sensor.object_id
    state_topic = _state_topic(cfg, oid)
    client.publish(state_topic, f"{value:.1f}", retain=True)
    log.info("published %s = %.1f", oid, value)


def publish_dark(cfg: Config, value: float, client: mqtt.Client) -> None:
    if not cfg.dark_sensor:
        return
    oid = cfg.dark_sensor.object_id
    is_dark = "ON" if value < cfg.dark_sensor.threshold else "OFF"
    state_topic = _state_topic(cfg, oid)
    client.publish(state_topic, is_dark, retain=True)
    log.info("published %s = %s (threshold %.0f)", oid, is_dark, cfg.dark_sensor.threshold)


def publish_discovery(cfg: Config, client: mqtt.Client) -> None:
    """Announce sensors to HA via MQTT discovery (auto-creates the entities)."""
    payload = {
        "name": cfg.luminance_sensor.name,
        "unique_id": _unique_id(cfg, "luminance"),
        "state_topic": _state_topic(cfg, cfg.luminance_sensor.object_id),
        "device_class": cfg.luminance_sensor.device_class,
        "unit_of_measurement": cfg.luminance_sensor.unit_of_measurement,
        "force_update": True,
    }
    t = _discovery_topic(cfg, _DISCOVERY, cfg.luminance_sensor.object_id)
    client.publish(t, json.dumps(payload), retain=True)
    log.info("discovered sensor %s", cfg.luminance_sensor.object_id)

    if cfg.dark_sensor:
        dark_payload = {
            "name": cfg.dark_sensor.name,
            "unique_id": _unique_id(cfg, "dark"),
            "state_topic": _state_topic(cfg, cfg.dark_sensor.object_id),
            "device_class": "motion",  # closest available; brightness isn't a binary_sensor class
            "payload_on": "ON",
            "payload_off": "OFF",
            "force_update": True,
        }
        dt = _discovery_topic(cfg, _BINARY_DISCOVERY, cfg.dark_sensor.object_id)
        client.publish(dt, json.dumps(dark_payload), retain=True)
        log.info("discovered binary_sensor %s", cfg.dark_sensor.object_id)


def build_client(cfg: Config) -> mqtt.Client:
    client = mqtt.Client(
        client_id=f"luminance_probe_{cfg.luminance_sensor.object_id}",
        protocol=mqtt.MQTTv311,
    )
    if cfg.mqtt.username:
        client.username_pw_set(cfg.mqtt.username, cfg.mqtt.password)
    client.enable_logger(log)
    return client


def connect(client: mqtt.Client, cfg: Config) -> None:
    client.connect(cfg.mqtt.host, cfg.mqtt.port, keepalive=60)
    client.loop_start()


def disconnect(client: mqtt.Client) -> None:
    client.loop_stop()
    client.disconnect()
