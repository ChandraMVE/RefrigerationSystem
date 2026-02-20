"""Configuration models for the walk-in refrigeration controller."""

from dataclasses import dataclass


@dataclass
class WalkInDimensionsFt:
    length: float = 10.0
    width: float = 10.0
    height: float = 10.0

    @property
    def volume_ft3(self) -> float:
        return self.length * self.width * self.height


@dataclass
class ControlConfig:
    target_temp_c: float = 2.0
    hysteresis_c: float = 1.0
    compressor_min_off_s: int = 120
    defrost_interval_s: int = 6 * 60 * 60
    defrost_duration_s: int = 20 * 60
