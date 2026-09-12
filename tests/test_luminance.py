"""Unit tests for luminance computation and config parsing."""
from PIL import Image

from lumina_probe.config import parse_config
from lumina_probe.luminance import luminance_rgb


def _img(pixel) -> Image.Image:
    return Image.new("RGB", (10, 10), pixel)


def test_black_is_zero():
    assert luminance_rgb(_img((0, 0, 0))) == 0.0


def test_white_is_255():
    # rec601 weighted: 0.299+0.587+0.114 = 1.0 -> 255
    assert luminance_rgb(_img((255, 255, 255))) == 255.0


def test_mid_gray():
    v = luminance_rgb(_img((128, 128, 128)))
    assert abs(v - 128.0) < 0.5


def test_red_darker_than_green():
    # green carries 0.587 weight, red 0.299 -> green should be brighter
    assert luminance_rgb(_img((255, 0, 0))) < luminance_rgb(_img((0, 255, 0)))


def test_parse_config_minimal():
    cfg = parse_config({
        "sources": [{"name": "cam", "url": "http://x/latest.jpg"}],
        "mqtt": {"host": "127.0.0.1"},
        "aggregate": "mean",
    })
    assert cfg.aggregate == "mean"
    assert cfg.sources[0].name == "cam"
    assert cfg.mqtt.host == "127.0.0.1"


def test_parse_config_dark_sensor():
    cfg = parse_config({
        "sources": [{"name": "cam", "url": "http://x"}],
        "mqtt": {"host": "h"},
        "sensor": {"is_dark": {"threshold": 30}},
    })
    assert cfg.dark_sensor is not None
    assert cfg.dark_sensor.threshold == 30.0
