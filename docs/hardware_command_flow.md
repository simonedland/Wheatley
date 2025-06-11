# Hardware Command Reference

## UART Interface

- **Baud rate**: 115200
- **Data bits**: 8
- **Stop bits**: 1
- **Parity**: None

The PC communicates with the M5Stack Core2 over USB serial. The Core2 forwards commands to the OpenRB-150 board.

## Command List

| Command | Parameters | Description |
|---------|------------|-------------|
| `HELLO` | – | Handshake message from OpenRB-150. The Core2 replies with `ESP32`. |
| `SET_LED` | `R=0..255;G=0..255;B=0..255` | Set all NeoPixels to a colour. |
| `SET_MIC_LED` | `IDX=n;R=..;G=..;B=..` | Set the microphone status LED. |
| `MOVE_SERVO` | `ID=n;TARGET=deg;VELOCITY=deg/s` | Move a single servo. |
| `SET_SERVO_CONFIG` | `id,target,velocity,idle_range,interval;...` | Bulk configuration for all servos. |
| `GET_SERVO_CONFIG` | – | Request servo limits; Core2 replies with `SERVO_CONFIG:` line. |

## Protocol Flow

1. After power on the OpenRB-150 sends `HELLO`. The Core2 replies `ESP32` and begins calibration.
2. Servo limits are reported as `id,min,max,ping;...`.
3. During operation the host sends `SET_SERVO_CONFIG` or individual `MOVE_SERVO` commands based on the selected animation.
4. LED updates use `SET_LED` and `SET_MIC_LED` for visual feedback.

Timeouts of 10 seconds are used during the initial handshake. If no handshake is received the Core2 enters demo mode.

## State Diagram

```
[Disconnected] --HELLO--> [Handshake]
[Handshake] --SERVO_CONFIG--> [Active]
[Active] --timeout--> [DemoMode]
```
