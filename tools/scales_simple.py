import serial
import time
from datetime import datetime

serial_object = serial.Serial(port = "/dev/ttyUSB1", baudrate = 115200, timeout = 1)
time.sleep(1)

while (serial_object.in_waiting > 18):
	serial_object.readline()

print("Buffer Cleared")
print("ID, Timestamp, Data, Bytes in Buffer")

for i in range(10):
	print(i, datetime.now().timestamp(), serial_object.readline(), serial_object.in_waiting)

print(serial_object.in_waiting)




