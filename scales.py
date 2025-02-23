###############################################################################
# This script is run as process and waits for one of the two scales to be triggered
# When the scales are empty for a certain period of time, the data is saved to file
###############################################################################



###############################################################################
# Imports
###############################################################################
import traceback
import sys
import os
import serial
import serial.tools.list_ports
from datetime import datetime
import threading
import json
from time import sleep
import statistics
from apms_email import email
from shared_functions import *
###############################################################################


###############################################################################
# Global variables dictionary
###############################################################################
CONFIG = {}
saving_flag = 0

###############################################################################
# Classes
###############################################################################
class Scale:
	def __init__(self, name):
		self.name = name
		self.serial_number = None
		self.serial_port = None
		self.serial_object = None
		self.weight_list = [] 		# List of tuples: (timestamp, weight)
		self.sand_build_up = False
		self.active	= False
		self.serial_buffer_max = 0
		self.error_count = 0

	
	###########################################################################
	# This function checks if there is a high dead weight on the scale
	###########################################################################
	def check_dead_weight(self):
		NUM_SAMPLES_HISTORY = int(CONFIG['SCALE_EMPTY_TIME'] * CONFIG['SCALE_SAMPLING_FREQ'])
		
		# First check to see we have enough samples to calculate dead weight
		if len(self.weight_list) < NUM_SAMPLES_HISTORY:
			return

		weights_only_list = [weight[1] for weight in self.weight_list]
		dead_weight = statistics.mode(weights_only_list)

		if dead_weight > CONFIG['MAX_DEAD_WEIGHT'] and dead_weight < CONFIG['MIN_PENGUIN_WEIGHT']:
			
			if self.sand_build_up == False:
				self.sand_build_up = True
				print("Check dead weight on {}: {} kg".format(self.name, dead_weight))
			
		elif dead_weight < CONFIG['MAX_DEAD_WEIGHT']:
			if self.sand_build_up == True:
				self.sand_build_up = False
				print("Dead weight on {} reduced to acceptable level".format(self.name))
###############################################################################




###############################################################################
# This function creates 2 scale objects and configures the required attributes
###############################################################################
def setup_scales ():

	scale_1 = Scale(name = "scale_1")
	scale_1.serial_number = CONFIG['SCALE_1_SERIAL_NUMBER']
	
	scale_2 = Scale(name = "scale_2")
	scale_2.serial_number = CONFIG['SCALE_2_SERIAL_NUMBER']

	print("Identifying Serial Ports...")
	ports = serial.tools.list_ports.comports()
	for port in ports:
		if (port.serial_number == scale_1.serial_number):
			print("Serial port for Scale 1 is: {} ".format(port.device)) 
			scale_1.serial_port = port.device
			scale_1.active = True

		if (port.serial_number == scale_2.serial_number):
			print("Serial port for Scale 2 is: {}".format(port.device)) 
			scale_2.serial_port = port.device
			scale_2.active = True

	if scale_1.serial_port == None:
		print("Could not identify scale 1 serial port. Scale deactivated")
		scale_1.active = False

	if scale_2.serial_port == None:
		print("Could not identify scale 2 serial port. Scale deactivated")
		scale_2.active = False

	if (scale_1.active == False and scale_2.active == False):
		print("Both scale serial ports could not be determined.")
		sys.exit()

	scale_1.serial_object = serial.Serial(port = scale_1.serial_port, baudrate = CONFIG['SCALE_BAUD_RATE'], timeout = 1)
	scale_2.serial_object = serial.Serial(port = scale_2.serial_port, baudrate = CONFIG['SCALE_BAUD_RATE'], timeout = 1)

	# Throw away first weight
	scale_1.serial_object.readline()
	scale_2.serial_object.readline()

	return scale_1, scale_2
###############################################################################



###############################################################################
# This function reads the scales, updates their weight lists and balances their serial port buffers
###############################################################################
def update_weight_lists (scale_1, scale_2):

	# Get a timestamp
	timestamp = datetime.now().timestamp()

	# Update max buffer if needed
	serial_buffer_1 = scale_1.serial_object.in_waiting
	serial_buffer_2 = scale_2.serial_object.in_waiting
	if serial_buffer_1 > scale_1.serial_buffer_max:
		if serial_buffer_1 > 16:
			print("Serial Buffer 1 Increase: ", serial_buffer_1)
		scale_1.serial_buffer_max = serial_buffer_1
	if serial_buffer_2 > scale_2.serial_buffer_max:
		if serial_buffer_2 > 16:
			print("Serial Buffer 2 Increase: ", serial_buffer_2)
		scale_2.serial_buffer_max = serial_buffer_2

	# Read Scale 1 then Scale 2. They return 0 if all went well
	if read_scale(scale_1, timestamp) or read_scale(scale_2, timestamp):
		return 1

	# Balance the serial buffers. One scale always reads a bit faster than the other, causing imbalance
	if scale_1.active == True and scale_2.active == True:
		
		if scale_1.serial_object.in_waiting < 8 and scale_2.serial_object.in_waiting > 8:
			print("Clearing byte from scale 2 serial buffer")
			scale_2.serial_object.readline()

		elif scale_2.serial_object.in_waiting < 8 and scale_1.serial_object.in_waiting > 8:
			print("Clearing byte from scale 1 serial buffer")
			scale_1.serial_object.readline()
###############################################################################



###############################################################################
# This function reads the scale weight and checks for errors.
###############################################################################
def read_scale (scale, timestamp):
	if scale.active == True:
		try:
			weight_bytes = scale.serial_object.readline()
			weight = int(weight_bytes.strip().decode())

			scale.weight_list.append((timestamp, weight/1000))
			return 0

		except Exception as e:
			print("Error reading ", scale.name)
			response = handle_scale_error(scale, weight_bytes, e)
			if response == 1:
				return 1
			else:
				scale.weight_list.append((timestamp, 0))
	else:
		scale.weight_list.append((timestamp, 0))
		return 0
###############################################################################



###############################################################################
def handle_scale_error (scale, weight_bytes, e):
	message = "APMS - scale error\n"
	message += "Site: {}\n".format(CONFIG["SITE_NAME"])

	scale.error_count = scale.error_count + 1
	message += "Error Count: {}/{}\n".format(scale.error_count, CONFIG["MAX_SCALE_ERROR_COUNT"])

	# Check if scale has failed too many times
	if scale.error_count > CONFIG["MAX_SCALE_ERROR_COUNT"]:
		message += "Error reading {}: Error: {} weight_bytes: {}".format(scale.name, e, weight_bytes)
		message += "{} has failed more than {} times. Disabling scale\n".format(scale.name, CONFIG["MAX_SCALE_ERROR_COUNT"])
		print(message)
		send_email_background(message)
	
		scale.active = False
		print("System now running on one scale only ({} disabled)".format(scale.name))
		return 1
	###########################################################################
	# This pops up randomly. Still investigating where this is coming from.
	# Not restarting scales for this, just making this sample 0 for now
	if weight_bytes == b'\xb777215\r\n':
		message += "----Bytes error: xb777215\n"
		print(message)
		return 0

	elif weight_bytes == b'\xb777216\r\n':
		message += "----Bytes error: xb777216\n"
		print(message)
		return 0
	###########################################################################

	# Scale overload detected
	elif weight_bytes == b' ER OL\r\n':
		message += "Overload\n"

	# Loadcell error
	elif weight_bytes == b' ERCEL\r\n':
		message += "Load cell error\n"

	# Unknown scale message (Refer to TLB485 Manual to identify message sent)
	else:
		message += "Error reading {}: Error: {} weight_bytes: {}".format(scale.name, e, weight_bytes)

	print(message)
	send_email_background(message)

	return 1
###############################################################################



###############################################################################
# This function records and saves the penguin event to file
###############################################################################
def record_event (scale_1, scale_2):

	# create a file called "busy" using touch to show event in progress
	os.system("touch busy")

	event_flag = True

	day = datetime.now().strftime("%Y%m%d")
	year =  datetime.now().strftime("%Y")
	event_date_time = datetime.now().strftime("%Y%m%d%H%M%S")
	filename = "S" + event_date_time + CONFIG["SITE_CODE"] + ".csv"
	data_dir = os.path.join(CONFIG["DATA_PATH"], year, day, 'scale')
	if_not_then_make(data_dir)
	filename_with_path = os.path.join(data_dir, filename)

	# This is used to keep an eye on the serial buffer
	serial_buffer_1 = scale_1.serial_object.in_waiting
	serial_buffer_2 = scale_2.serial_object.in_waiting
	print("Max serial 1 buffer: {}/128".format(scale_1.serial_buffer_max))
	print("Max serial 2 buffer: {}/128".format(scale_2.serial_buffer_max))

	while (event_flag == True):
		
		if update_weight_lists (scale_1, scale_2) == 1:
			print("Scale failure during event")
			# save_error_file (scale_1, scale_2, filename)
			os.system("rm busy")
			print("Restarting scales...")
			restart_scales(scale_1, scale_2)
			return
		
		else:
			scale_1_weight = scale_1.weight_list[-1][1]
			scale_2_weight = scale_2.weight_list[-1][1]
		
			if (scale_1_weight < CONFIG["MAX_DEAD_WEIGHT"] and scale_2_weight < CONFIG["MAX_DEAD_WEIGHT"]):
				
				# Both scales are empty, check if the remain empty and stop event
				response = check_end_of_event(scale_1, scale_2)
	
				if response == True:
					event_flag = False

				elif response == "error":
					save_file (scale_1, scale_2, filename)
					os.system("rm busy")
					print("Restarting scales...")
					restart_scales(scale_1, scale_2)
					return

	print ("{} - Scale event finished.".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
	
	print("Saving to {}\n".format(filename_with_path))
	
	save_file_thread = threading.Thread(target=save_to_file, args=(filename_with_path, scale_1, scale_2))
	save_file_thread.start()
	
	# delete file called "busy" as event has finished
	os.system("rm busy")
###############################################################################

###############################################################################
# This function sends an email in the background using threading
###############################################################################
def send_email_background(message):
	email_thread = threading.Thread(target=email, args=(message,))
	email_thread.start()
###############################################################################




###############################################################################
# This function is used to clear the serial buffers and weight lists of the scales
###############################################################################
def restart_scales (scale_1, scale_2):

	# Empty scale buffers
	while True:
		# Slow down the reading to ensure buffer is completely empty		
		if scale_1.serial_object.in_waiting > 8:
			sleep(0.005)
			scale_1.serial_object.readline()

		elif scale_2.serial_object.in_waiting > 8:
			sleep(0.005)
			scale_2.serial_object.readline()

		else:
			break

	scale_1.weight_list = []
	scale_2.weight_list = []
###############################################################################



###############################################################################
# This function checks if the scales remain empty long enough to end event
###############################################################################
def check_end_of_event (scale_1, scale_2):

	# start dead time timer 	
	dead_timer_flag = True
	dead_time_start = datetime.now()

	while True:

		if update_weight_lists(scale_1, scale_2) == 1:
			print("Scale failure after event")
			return "error"
		
		else:
			scale_1_weight = scale_1.weight_list[-1][1]
			scale_2_weight = scale_2.weight_list[-1][1]

			if (scale_1_weight > CONFIG["MAX_DEAD_WEIGHT"] or scale_2_weight > CONFIG["MAX_DEAD_WEIGHT"]):
				return False

			# Timer has run out
			if (datetime.now().timestamp() - dead_time_start.timestamp()) > CONFIG["SCALE_EMPTY_TIME"]:
				return True
###############################################################################



###############################################################################
# This function saves the scale weights to a file
###############################################################################
def save_to_file (filename_with_path, scale_1, scale_2):


	global saving_flag
	saving_flag = 1

	# Event finished. Write data to file
	with open(filename_with_path, 'w') as file:

		num_of_weights = min( len(scale_1.weight_list), len(scale_2.weight_list) )

		for i in range(num_of_weights):
			timestamp = scale_1.weight_list[i][0]
			scale_1_weight = scale_1.weight_list[i][1]
			scale_2_weight = scale_2.weight_list[i][1]
			# print("timestamp, scale_1_weight, scale_2_weight")
			# print(timestamp, scale_1_weight, scale_2_weight)
			# file.write("{}, {}, {}\n".format(timestamp, scale_1_weight, scale_2_weight))
			file.write( "%s, %.6f, %.6f \n" % (timestamp, scale_1_weight, scale_2_weight))

	saving_flag = 0
	print ("File saved")
###############################################################################



###############################################################################
# This function creates a directory if it does not already exist
###############################################################################
def if_not_then_make (path):
	if not os.path.exists(path):
		os.makedirs(path)
##############################################################################



###############################################################################
# This function checks that the weight list only holds a certain number of samples as history
###############################################################################
def reduce_weight_lists (scale_1, scale_2):
	MIN_SAMPLES = int(CONFIG['SCALE_EMPTY_TIME'] * CONFIG['SCALE_SAMPLING_FREQ'])
	while len(scale_1.weight_list) > MIN_SAMPLES:
		scale_1.weight_list.pop(0)
	while len(scale_2.weight_list) > MIN_SAMPLES:
		scale_2.weight_list.pop(0)
###############################################################################



###############################################################################
# This function saves the current scale data to an error file
###############################################################################
def save_error_file (scale_1, scale_2):
	error_dir = os.path.join(CONFIG["ERROR_PATH"])
	if_not_then_make(error_dir)
	closing_time = datetime.now().strftime("%Y%m%d%H%M%S")
	filename = "scale_file_incomplete_{}.csv".format(closing_time)
	filename_with_path = os.path.join(error_dir, filename)
	print("filename: ", filename)
	save_to_file(filename_with_path, scale_1, scale_2)
	print ("{}: Scale reading failed. data saved to: ".format(filename_with_path))
###############################################################################


###############################################################################
# Main function 
###############################################################################
try:
	print("scales.py running...")
	
	# Load config.json
	CONFIG = load_config_file()

	# Configure and connect to scales
	scale_1, scale_2 = setup_scales()

	# Clear any weights in the serial buffer
	restart_scales(scale_1, scale_2)

	print("Weighbridge running...")

	while True:
		
		# Update the weight list for each scale. If reading failed, restart scales
		if update_weight_lists(scale_1, scale_2) == 1:
			save_error_file(scale_1, scale_2)
			print("Scale failure during idle. Restarting scales...")
			restart_scales(scale_1, scale_2)
			continue


		# Check if there is a sand build-up on the scales
		scale_1.check_dead_weight()
		scale_2.check_dead_weight()

		# Get the last weight from each scale and if greater than min penguin weight, start event
		scale_1_weight = scale_1.weight_list[-1][1]
		scale_2_weight = scale_2.weight_list[-1][1]

		if (scale_1_weight > CONFIG["MIN_PENGUIN_WEIGHT"]):
			print("{} - Scale 1 has been triggered. Heading out to ocean.".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
			record_event(scale_1, scale_2)

		elif (scale_2_weight > CONFIG["MIN_PENGUIN_WEIGHT"]):
			print("{} - Scale 2 has been triggered. coming back from the ocean.".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
			record_event(scale_1, scale_2)

		if saving_flag == 0:
			reduce_weight_lists(scale_1, scale_2)

except (KeyboardInterrupt):
	save_error_file(scale_1, scale_2)
	print("\nscales.py closed by user. Goodbye")
	sys.exit()

except Exception as e:

	save_error_file(scale_1, scale_2)
	print("\nA problem occured while running the scales.py script - {}. Error: {}".format(CONFIG["SITE_NAME"], e))
	email("A problem occured while running the scales.py script - {}. Error: {}".format(CONFIG["SITE_NAME"], e))

	traceback.print_exc()
	print("Waiting for 1 hour before closing...")
	# Wait for 1 hour, system should then try and run the script again
	sleep(3600)
	sys.exit()
###############################################################################




