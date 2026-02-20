# UART Message Protocol

## 1. SCK command interface

Quick actions for **Monitor UART** and **IO UART** use the SCK command frame now.
Frames are sent as a hex line in the simulator UI:

- `SCK <byte0> <byte1> ... <byteN>`
- Example: `SCK 02 20 04 03 00 01 43 02 00 85 31 03`

### Frame layout

| Field | Size | Description |
|---|---:|---|
| HEADER | 1 | `0x02` (STX) |
| VERSION | 2 | LSB first (`VERSION LOW`, `VERSION HI`) |
| LENGTH | 2 | LSB first length of `C/S + CMD(2) + PAYLOAD` |
| TID | 1 | Transaction ID |
| C or S | 1 | `0x43` for Command (`C`), `0x53` for Status (`S`) |
| CMD | 2 | LSB first command id |
| PAYLOAD | N | Command specific bytes |
| CRC | 2 | CRC-16 over `LENGTH + C/S + CMD + PAYLOAD` |
| TRAILER | 1 | `0x03` (ETX) |

## 2. Command map

### Monitor UART (`C` frames)
- `0x0001`: set config, payload is `key=value`
- `0x0002`: get config
- `0x0003`: get status

### IO UART (`C` frames)
- `0x0101`: set sensor, payload is `air_temp_c=<float>`
- `0x0102`: set input, payload is `<input_key>=<0|1>`
- `0x0103`: get IO snapshot

## 3. Status responses

Controller responses are returned as `S` frames, using the same command id and TID as the request.
The payload remains human-readable text (`ACK ...`, `ERR ...`, `CONFIG ...`, `STATUS ...`, `IO ...`) so logs are still easy to inspect.

## 4. Backward compatibility

The legacy text protocol (`SET ...`, `GET ...`) is still accepted for manual testing.
