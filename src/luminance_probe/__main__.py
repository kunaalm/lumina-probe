"""luminance-probe: measure image luminance and publish to MQTT."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from .config import Config, load_config
from .luminance import aggregate, compute_sources
from . import mqtt

log = logging.getLogger("luminance_probe")

_RUNNING = True


def _handle_signal(signum, frame):
    global _RUNNING
    log.info("signal %s received, shutting down", signum)
    _RUNNING = False


def _publish_all(cfg: Config, client, per_source: dict) -> None:
    # always publish discovery once per cycle so HA re-creates the sensor if cleared
    mqtt.publish_discovery(cfg, client)
    for name, value in per_source.items():
        log.info("source %s luminance=%.1f", name, value)
    agg_value = aggregate(per_source, cfg.aggregate)
    if agg_value is None:
        log.warning("no sources produced a luminance value this cycle")
        return
    value = agg_value * cfg.lux_gain if cfg.lux_enabled else agg_value
    mqtt.publish_luminance(cfg, value, client)
    mqtt.publish_dark(cfg, agg_value, client)


def run_forever(cfg: Config) -> None:
    client = mqtt.build_client(cfg)
    mqtt.connect(client, cfg)
    try:
        while _RUNNING:
            per_source = compute_sources(cfg.sources)
            _publish_all(cfg, client, per_source)
            # wait in small slices so signals interrupt promptly
            for _ in range(max(1, int(cfg.interval_seconds / 1))):
                if not _RUNNING:
                    break
                time.sleep(1)
    finally:
        mqtt.disconnect(client)


def run_once(cfg: Config) -> int:
    per_source = compute_sources(cfg.sources)
    if not per_source:
        log.error("no source produced a frame")
        return 1
    client = mqtt.build_client(cfg)
    mqtt.connect(client, cfg)
    try:
        _publish_all(cfg, client, per_source)
        time.sleep(1)  # let retained messages flush
    finally:
        mqtt.disconnect(client)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Measure image luminance, publish to MQTT.")
    parser.add_argument("--config", default="config.yaml", help="path to YAML config")
    parser.add_argument("--once", action="store_true", help="poll once then exit (for testing)")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if args.once:
        return run_once(cfg)
    run_forever(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
