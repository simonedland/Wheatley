# Wiring Diagram

Below is the wiring overview of the system. The original image shows connections between the ESP32, OpenRB-150 and the Dynamixel servos.

## Pinout Tables

| Pin | Signal | Notes |
|-----|--------|------|
| 13  | RX2    | UART from OpenRB-150 |
| 14  | TX2    | UART to OpenRB-150 |
| 27  | LED    | NeoPixel strip data |

### OpenRB-150

| Pin | Voltage |
|-----|---------|
| VIN | 5V      |
| GND | Ground  |
| TX3 | UART TX |
| RX3 | UART RX |

## Legend

- **Red wires** – power lines (5V)
- **Black wires** – ground
- **Blue wires** – UART communication
- **Green wires** – signal lines to servos

Each connector in the diagram is labeled for clarity so the hardware can be assembled without referencing the schematic.
