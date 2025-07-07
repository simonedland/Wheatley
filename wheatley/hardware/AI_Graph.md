# AI Directory Structure

```mermaid
graph TD
    arduino_interface_py["arduino_interface.py"]
    arduino_interface_py -->|uses| ServoController
    arduino_interface_py -->|uses| Servo
    arduino_interface_py -.->|imports| serial
```
