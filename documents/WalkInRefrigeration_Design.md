# Walk-In Refrigeration System (10ft x 10ft x 10ft) - Initial Design

## 1. Scope
This branch introduces a Python-first skeleton for a walk-in refrigeration controller.
The Python implementation is intentionally modular so we can later port control logic to C
with minimal dependencies and IO coupling.

## 2. Physical System
- Dimensions: **10ft x 10ft x 10ft** (L x W x H)
- Volume: **1000 ft³**
- Target use: Walk-in refrigerator

## 3. Two-UART Strategy
The architecture uses two UART channels:

1. **UART_MONITOR** (real refrigeration monitor channel)
   - Human-facing monitor/display side.
   - Exposes configurable parameters such as:
     - target temperature
     - compressor minimum off-time
     - defrost interval
     - defrost duration
   - Emits periodic status snapshots.

2. **UART_IO_MIMIC** (IO-line mimic channel)
   - Simulates digital/analog IO behaviors in software.
   - Accepts commands to override simulated sensors and states.
   - Returns acknowledgement and current simulated line values.

## 4. Software Layering
The skeleton is split into clean layers:

- `config.py`
  - Holds tunable control settings and walk-in dimensions.
- `uart.py`
  - Defines UART transport abstractions and an in-memory mock transport.
- `controller.py`
  - Core control loop skeleton independent from concrete UART implementation.
- `app.py`
  - Wiring/bootstrap for local simulation using mock UARTs.

This split is chosen to make C-porting easier:
- control decisions remain in `controller.py` with low IO assumptions.
- UART-specific logic remains isolated.

## 5. Immediate Next Steps
1. Add explicit finite-state machine for cooling/idle/defrost/fault states.
2. Add sensor plausibility checks and alarm handling.
3. Add persistence for configuration parameters.
4. Define fixed message framing suitable for eventual C implementation.
5. Add unit tests around control decisions and UART command parsing.
