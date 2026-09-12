"""Config loading + validation for luminance-probe."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


class ConfigError(Exception):
    pass


@dataclass
class Source:
    name: str
    url: str


@dataclass
class MQTTConfig:
    host: str
    port: int = 1883
    username: str = ""
    password: str = ""
    topic: str = "homeassistant"


@dataclass
class LuminanceSensor:
    name: str = "Luminance"
    object_id: str = "luminance"
    unit_of_measurement: str = ""
    device_class: str = ""


@dataclass
class DarkSensor:
    name: str = "Is Dark"
    object_id: str = "is_dark"
    threshold: float = 30.0


@dataclass
class Config:
    interval_seconds: int = 300
    sources: List[Source] = field(default_factory=list)
    aggregate: str = "mean"
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    luminance_sensor: LuminanceSensor = field(default_factory=LuminanceSensor)
    dark_sensor: Optional[DarkSensor] = None
    lux_enabled: bool = False
    lux_gain: float = 4.0
    log_level: str = "INFO"

    @property
    def sources_by_name(self) -> dict:
        return {s.name: s for s in self.sources}


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise ConfigError(f"config file not found: {path}")
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return parse_config(raw)


def parse_config(raw: dict) -> Config:
    sources_raw = raw.get("sources") or []
    if not sources_raw:
        raise ConfigError("config must define at least one source")
    sources = [
        Source(name=s.get("name", f"source{i}"), url=s.get("url", ""))
        for i, s in enumerate(sources_raw)
    ]
    for s in sources:
        if not s.url:
            raise ConfigError(f"source '{s.name}' has no url")

    agg = raw.get("aggregate", "mean")
    if agg not in ("per_source", "mean", "median", "min"):
        raise ConfigError(f"invalid aggregate '{agg}'")

    m = raw.get("mqtt") or {}
    # allow password via env override (never bake secrets into files)
    mqtt_password = m.get("password", "") or os.environ.get("MQTT_PASSWORD", "")
    mqtt = MQTTConfig(
        host=m.get("host", ""),
        port=int(m.get("port", 1883)),
        username=m.get("username", ""),
        password=mqtt_password,
        topic=m.get("topic", "homeassistant"),
    )
    if not mqtt.host:
        raise ConfigError("mqtt.host is required")

    ls = raw.get("sensor", {}).get("luminance", {}) or {}
    lum_sensor = LuminanceSensor(
        name=ls.get("name", "Luminance"),
        object_id=ls.get("object_id", "luminance"),
        unit_of_measurement=ls.get("unit_of_measurement", ""),
        device_class=ls.get("device_class", ""),
    )

    dark = raw.get("sensor", {}).get("is_dark")
    dark_sensor = None
    if dark:
        dark_sensor = DarkSensor(
            name=dark.get("name", "Is Dark"),
            object_id=dark.get("object_id", "is_dark"),
            threshold=float(dark.get("threshold", 30.0)),
        )

    lux = raw.get("lux") or {}
    poll = raw.get("poll") or {}

    return Config(
        interval_seconds=int(poll.get("interval_seconds", 300)),
        sources=sources,
        aggregate=agg,
        mqtt=mqtt,
        luminance_sensor=lum_sensor,
        dark_sensor=dark_sensor,
        lux_enabled=bool(lux.get("enabled", False)),
        lux_gain=float(lux.get("gain", 4.0)),
        log_level=raw.get("log_level", "INFO"),
    )
