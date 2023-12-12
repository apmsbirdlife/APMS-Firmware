import sys
import os.path
import serial.tools.list_ports

print("Welcome to the RS485 SN Identification Tool")
try:
	print("Please disconnect all USB devices and press ENTER")
	input()
	print("Now plug the serial converter into any of the USB ports and press ENTER")
	input()
	ports = serial.tools.list_ports.comports()
	print("Serial number detected: {}".format(ports[0].serial_number))
	print("Thank you. Goodbye")

except (KeyboardInterrupt):
	sys.exit()

	
