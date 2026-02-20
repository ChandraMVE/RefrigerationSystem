# UART Message Protocol (Draft)

This is a text-based draft protocol for rapid Python development.
Later we can evolve this into fixed-width or binary framing for C.

## 1. UART_MONITOR
### Incoming commands
- `SET target_temp_c=<float>`
- `SET compressor_min_off_s=<int>`
- `SET defrost_interval_s=<int>`
- `SET defrost_duration_s=<int>`
- `GET CONFIG`
- `GET STATUS`

### Outgoing responses
- `ACK <field>=<value>`
- `CONFIG <key=value, ...>`
- `STATUS <key=value, ...>`
- `ERR <reason>`

## 2. UART_IO_MIMIC
### Incoming commands
- `SET_SENSOR air_temp_c=<float>`
- `SET_INPUT door_open=<0|1>`
- `SET_INPUT power_ok=<0|1>`
- `SET_INPUT motion_detected=<0|1>`
- `SET_INPUT panic_button_pressed=<0|1>`
- `GET IO`

### Outgoing responses
- `ACK <field>=<value>`
- `IO <key=value, ...>`
- `ERR <reason>`

## 3. Notes
- Commands are newline-terminated text frames.
- Parsing is key=value based for readability while prototyping.
- A version marker should be added before hardware integration.
