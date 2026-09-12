# luminance-probe

Poll any set of HTTP image sources (RTSP camera snapshots, MJPEG endpoints,
Frigate `latest.jpg`, WebDAV thumbnails...), compute the average *luminance*
(perceived brightness) of each frame, and publish the result to an MQTT broker
with [Home Assistant MQTT discovery](https://www.home-assistant.io/integrations/mqtt/)
so a `sensor.*` is created automatically.

A common use is deriving an *outdoor ambient light* reading from cameras you
already own — real light measured from the pixels, not a weather forecast.

```
[HTTP sources] ──poll──▶ [compute luminance] ──publish──▶ [MQTT] ──▶ [Home Assistant]
   4× front cams            per-frame, Rec.709         retained          sensor.outdoor_luminance
```

## Why this shape

- **Config-driven, not coded.** Everything — which URLs to poll, how to
  aggregate them, the MQTT broker, the sensor names, thresholds — lives in one
  YAML file. No homelab values are hardcoded in the image.
- **Decoupled.** The probe publishes on a timer and doesn't care whether Home
  Assistant is up. Retained messages mean the last reading survives a broker or
  HA restart.
- **Generic.** It is not tied to Frigate, to Home Assistant, or to any vendor.
  Point it at any URL that returns a JPEG/PNG and it measures brightness.

## Quick start

```bash
cp config/example.yaml config/config.yaml   # edit it
docker run --rm -v $(pwd)/config/config.yaml:/app/config.yaml \
  ghcr.io/kunaalm/luminance-probe:latest
```

## Config reference

See [`config/example.yaml`](config/example.yaml) for the full schema with
comments. In short:

| Key | Meaning |
|---|---|
| `poll.interval_seconds` | how often to poll and publish |
| `sources` | list of `{name, url}` image endpoints to measure |
| `aggregate` | `mean`, `median`, or `min` across sources, or `per_source` |
| `mqtt.host` / `port` | MQTT broker |
| `mqtt.username` / `password` | broker auth (or `MQTT_PASSWORD` env) |
| `mqtt.topic` | discovery base topic |
| `sensor.luminance` | name / device_class / unit for the sensor |
| `sensor.is_dark` | optional threshold → `binary_sensor` for dusk-gating |

## How luminance is computed

Each frame is converted to grayscale (Rec.601 weighted
`0.299R + 0.587G + 0.114B`), and the mean of the resulting channel is the
luminance value (`0–255`, with `0` = pure black). If you want an approximate
*lux*, the config `lux.gain` multiplies the 0–255 value (a common rule of thumb
is ~4×; the physically-correct value depends on your camera's exposure).

## Security

The image ships **no secrets**. Broker credentials are read from
`config.yaml` or the `MQTT_PASSWORD` environment variable — never baked in.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m luminance_probe --config config/example.yaml --once
```

## License

MIT — see [LICENSE](LICENSE).
