###############################################################################
# This script can be used to test the configuretaion of the scales and 
# to see at what frequency they are sampling
###############################################################################

import serial
import time
from datetime import datetime
from shared_functions import *
import serial.tools.list_ports

CONFIG = {}

def setup_scales ():

	scale_1_serial_number = CONFIG['SCALE_1_SERIAL_NUMBER']
	scale_2_serial_number = CONFIG['SCALE_2_SERIAL_NUMBER']

	print("Identifying Serial Ports...")
	ports = serial.tools.list_ports.comports()
	for port in ports:
		if (port.serial_number == scale_1_serial_number):
			print("Serial port for Scale 1 is: {} ".format(port.device)) 
			scale_1_serial_port = port.device
			
		if (port.serial_number == scale_2_serial_number):
			print("Serial port for Scale 2 is: {}".format(port.device)) 
			scale_2_serial_port = port.device
			
	scale_1_serial_object = serial.Serial(port = scale_1_serial_port, baudrate = CONFIG['SCALE_BAUD_RATE'], timeout = 1)
	scale_2_serial_object = serial.Serial(port = scale_2_serial_port, baudrate = CONFIG['SCALE_BAUD_RATE'], timeout = 1)

	frequency_scale_1 = check_frequency(scale_1_serial_object)
	print("Average Frequency Scale 1: {:.1f} Hz ".format(frequency_scale_1))

	frequency_scale_2 = check_frequency(scale_2_serial_object)
	print("Average Frequency Scale 2: {:.1f} Hz ".format(frequency_scale_2))






###############################################################################
def check_frequency (scale_serial_object):

	while (scale_serial_object.in_waiting > 0):
			sleep(0.005)
			scale_serial_object.readline()
	
	time_start = datetime.now().timestamp()
	for i in range (1,1000):
		# print("Serial Buffer: ", scale_serial_object.in_waiting)
		scale_serial_object.readline()
		time_now = datetime.now().timestamp()
		total_time_till_now = time_now - time_start
		delta_t_avg = total_time_till_now / i
		frequency_avg = 1/delta_t_avg
		# print("Average", frequency_avg)

	return frequency_avg

###############################################################################

CONFIG = load_config_file()
setup_scales()
