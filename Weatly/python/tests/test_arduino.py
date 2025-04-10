import unittest
from python.src.hardware.arduino_interface import ArduinoInterface

class TestArduinoInterface(unittest.TestCase):
    
    def setUp(self):
        self.arduino = ArduinoInterface(port='/dev/ttyUSB0')  # Adjust port as necessary

    def test_connection(self):
        self.assertTrue(self.arduino.connect(), "Failed to connect to Arduino")

    def test_send_data(self):
        result = self.arduino.send_data('test')
        self.assertTrue(result, "Failed to send data to Arduino")

    def test_receive_data(self):
        self.arduino.send_data('test')
        data = self.arduino.receive_data()
        self.assertEqual(data, 'test', "Received data does not match sent data")

    def tearDown(self):
        self.arduino.disconnect()

if __name__ == '__main__':
    unittest.main()