# collectors/

This directory contains concrete collector implementations.

Each module implements a single job source by subclassing `BaseCollector`
and implementing all abstract methods. Collectors are auto-discovered
by the `CollectorRegistry`.

## Adding a new collector

1. Create a new `.py` file in this directory.
2. Subclass `BaseCollector` and implement all abstract methods.
3. The registry will discover it automatically on the next scan.

See the parent `README.md` for detailed instructions.
