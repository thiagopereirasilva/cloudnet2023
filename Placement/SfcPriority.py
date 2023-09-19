from enum import Enum


class SfcPriority(Enum):
    latency = 1
    capacity = 2
    energy = 3
