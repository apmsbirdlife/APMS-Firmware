###############################################################################
# This script is run as process and waits for one of the two scales to be triggered
# When the scales are empty for a certain period of time, the data is saved to file
# This code is very much beta and can be made more efficient
###############################################################################


###############################################################################
# Imports
###############################################################################
import traceback
import multiprocessing
import sys
import os
import serial
import serial.tools.list_ports
from datetime import datetime, timedelta
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
		self.dead_weight = -999
		self.active	= False
		self.serial_buffer_max = 0
		self.error_count = 0

		
	###############################################################################
	# This method gets the dead weight on the scale. 
	###############################################################################
	def calculate_dead_weight(self):
		NUM_SAMPLES_HISTORY = int(CONFIG['SCALE_EMPTY_TIME']) * int(CONFIG['SCALE_SAMPLING_FREQ'])
		
		# First check to see we have enough samples to calculate dead weight
		if len(self.weight_list) < NUM_SAMPLES_HISTORY:
			return
		
		else:
			# weight is a tuple -> (timestamp, weight)
			weights_only_list = [weight[1] for weight in self.weight_list]
			dead_weight = statistics.mode(weights_only_list)


			if dead_weight < CONFIG["MIN_PENGUIN_WEIGHT"]/2:
				self.dead_weight = dead_weight
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
		if serial_buffer_1 > CONFIG["SCALE_WORD_LENGTH"]*2 and scale_1.active == True:
			print("Serial Buffer 1 Increase: ", serial_buffer_1)
		scale_1.serial_buffer_max = serial_buffer_1
	if serial_buffer_2 > scale_2.serial_buffer_max:
		if serial_buffer_2 > CONFIG["SCALE_WORD_LENGTH"]*2 and scale_2.active == True:
			print("Serial Buffer 2 Increase: ", serial_buffer_2)
		scale_2.serial_buffer_max = serial_buffer_2

	# Read Scale 1 then Scale 2. They return 0 if all went well
	if read_scale(scale_1, timestamp) or read_scale(scale_2, timestamp):
		return 1

	# Balance the serial buffers. One scale always reads a bit faster than the other, causing imbalance
	if scale_1.active == True and scale_2.active == True:

		if scale_1.serial_object.in_waiting < CONFIG["SCALE_WORD_LENGTH"] and scale_2.serial_object.in_waiting > CONFIG["SCALE_WORD_LENGTH"]:
			print("Clearing byte from scale 2 serial buffer")
			scale_2.serial_object.readline()

		elif scale_2.serial_object.in_waiting < CONFIG["SCALE_WORD_LENGTH"] and scale_1.serial_object.in_waiting > CONFIG["SCALE_WORD_LENGTH"]:
			print("Clearing byte from scale 1 serial buffer")
			scale_1.serial_object.readline()
###############################################################################


###############################################################################
# This function reads the scale weight and checks for errors.
###############################################################################
def read_scale (scale, timestamp):
	if scale.active == True:

		try:

			if CONFIG["SCALE_TYPE"] == "TLB4":

				weight_bytes = scale.serial_object.readline()

				### Added 5 Oct 2025 ###
				weight_bytes = weight_bytes.replace(b"\x00", b"")

				weight = int(weight_bytes.strip().decode())
				scale.weight_list.append((timestamp, weight/1000))
				return 0


			if CONFIG["SCALE_TYPE"] == "GMT-X1":

				weight_bytes = scale.serial_object.readline()

				### Added 3 Mar 2026 ###
				weight_bytes = weight_bytes.replace(b"\x00", b"")

				weight_ascii = weight_bytes.decode('ascii')
				weight_ascii = weight_ascii[weight_ascii.index("kg")-8:weight_ascii.index("kg")]
				weight_ascii = weight_ascii.replace(" ","")

				weight = float(weight_ascii)

				scale.weight_list.append((timestamp, weight))
				return 0

		except Exception as e:
			
			print(e)
			print("THIS WAS RECEIVED: {}".format(weight_bytes))
			
			scale.weight_list.append((timestamp, 0))
			scale.error_count += 1
			print("Reading error occured. Current error count for {} is {}".format(scale.name,scale.error_count))
			return 0
			
	else:
		scale.weight_list.append((timestamp, 0))
		return 0
###############################################################################




###############################################################################
# This function records and saves the penguin event to file
###############################################################################
def record_event (scale_1, scale_2):

	# create a file called "scales_busy" using touch to show event in progress
	os.system("touch ~/apms/scales_busy")

	event_flag = True

	start_time = datetime.now()
	day = start_time.strftime("%Y%m%d")
	year =  start_time.strftime("%Y")
	event_date_time = start_time.strftime("%Y%m%d%H%M%S")
	filename = "S" + event_date_time + CONFIG["SITE_CODE"] + ".csv"
	data_dir = os.path.join(CONFIG["DATA_PATH"], year, day, 'scale')
	if_not_then_make(data_dir)
	filename_with_path = os.path.join(data_dir, filename)

	# This is used to keep an eye on the serial buffer
	serial_buffer_1 = scale_1.serial_object.in_waiting
	serial_buffer_2 = scale_2.serial_object.in_waiting
	print("Serial 1 buffer: {}".format(serial_buffer_1))
	print("Serial 2 buffer: {}".format(serial_buffer_2))
	print("Max serial 1 buffer: {}".format(scale_1.serial_buffer_max))
	print("Max serial 2 buffer: {}".format(scale_2.serial_buffer_max))

	while (event_flag == True):

		# Check if the event has been more than 6 hours and alert operator
		event_duration = datetime.now() - start_time
		if event_duration >  timedelta(hours=6):
			send_email_background("An event of over 6 hours is currently happening at {}".format(CONFIG["SITE_NAME"]))
			break
		
		if update_weight_lists (scale_1, scale_2) == 1:
			
			print("Scale failure during event. Saving error file and restarting scales...")
			save_error_file(scale_1, scale_2)
			restart_scales(scale_1, scale_2)
			os.system("rm ~/apms/scales_busy")
			return
		
		else:

			scale_1_weight = scale_1.weight_list[-1][1]
			scale_2_weight = scale_2.weight_list[-1][1]
	
			if (scale_1_weight < CONFIG["MIN_PENGUIN_WEIGHT"]/2 and scale_2_weight < CONFIG["MIN_PENGUIN_WEIGHT"]/2):
				
				# Both scales are empty, check if they remain empty and stop event
				response = check_end_of_event(scale_1, scale_2)
	
				if response == True:
					event_flag = False

				elif response == "error":
					print("Scale failure during checking of end of event. Saving error file.")
					save_error_file(scale_1, scale_2)
					print("Restarting scales...")
					restart_scales(scale_1, scale_2)
					os.system("rm ~/apms/scales_busy")
					return

	print ("{} - Scale event finished.".format(start_time.strftime("%d/%m/%Y %H:%M:%S")))
	
	print("Saving to {}\n".format(filename_with_path))
	
	save_to_file (filename_with_path, scale_1, scale_2)
	
	# Create a Process for the save_to_file function
	# save_process = multiprocessing.Process(target=save_to_file, args=(filename_with_path, scale_1, scale_2))
	# save_process.start()

	# save_file_thread = threading.Thread(target=save_to_file, args=(filename_with_path, scale_1, scale_2))
	# save_file_thread.start()
	
	# delete file called "scales_busy" as event has finished
	os.system("rm ~/apms/scales_busy")
###############################################################################



###############################################################################
# This function sends an email in the background using threading
###############################################################################
def send_email_background(message):
	email_thread = threading.Thread(target=email, args=(message,))
	email_thread.start()
###############################################################################



###############################################################################
# This function is used to restart the scales in case of failure
###############################################################################
def restart_scales (scale_1, scale_2):
	print(scale_1.weight_list, scale_2.weight_list)
	sleep(60)
	# Empty scale buffers
	clear_scale_buffers (scale_1, scale_2)
	print("Scales have been restarted")
###############################################################################



###############################################################################
# This function is used to clear the serial buffers and weight lists of the scales
###############################################################################
def clear_scale_buffers (scale_1, scale_2):
	while True:
		# Slow down the reading to ensure buffer is completely empty		
		if scale_1.serial_object.in_waiting > 8:
			sleep(0.001)
			scale_1.serial_object.readline()

		elif scale_2.serial_object.in_waiting > 8:
			sleep(0.001)
			scale_2.serial_object.readline()
		else:
			break
	scale_1.weight_list = []
	scale_2.weight_list = []
###############################################################################





###############################################################################
# This function checks if the scales remain empty long enough to end event
# We want the scales to be empty for "SCALE_EMPTY_TIME" set in the config file 	
###############################################################################
def check_end_of_event (scale_1, scale_2):

	# start dead time timer. 
	dead_timer_flag = True
	dead_time_start = datetime.now()
	while True:
		if update_weight_lists(scale_1, scale_2) == 1:
			return "error"
		else:
			# Get last weight. weight_list tuple = (timestamp, weight)
			scale_1_weight = scale_1.weight_list[-1][1]
			scale_2_weight = scale_2.weight_list[-1][1]

			scale_1_net = scale_1_weight - scale_1.dead_weight
			scale_2_net = scale_2_weight - scale_2.dead_weight

			# One of the scales not empty
			if (scale_1_net > CONFIG["MIN_PENGUIN_WEIGHT"]/2 or scale_2_net > CONFIG["MIN_PENGUIN_WEIGHT"]/2):
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
	print("error filename: ", filename)
	save_to_file(filename_with_path, scale_1, scale_2)
	print ("Scale reading failed. data saved to: {} ".format(filename_with_path))
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
	clear_scale_buffers(scale_1, scale_2)

	print("Weighbridge running...")
	while True:
	
		# Update the weight list for each scale. If reading failed, restart scales
		if update_weight_lists(scale_1, scale_2) == 1:
			save_error_file(scale_1, scale_2)
			print("Scale failure during idle. Restarting scales...")
			restart_scales(scale_1, scale_2)
			continue

		scale_1.calculate_dead_weight()
		scale_2.calculate_dead_weight()

		# Get the last weight from each scale and if greater than min penguin weight, start event
		scale_1_weight = scale_1.weight_list[-1][1]
		scale_2_weight = scale_2.weight_list[-1][1]
		
		scale_1_net = scale_1_weight - scale_1.dead_weight
		scale_2_net = scale_2_weight - scale_2.dead_weight

		if ( scale_1_net > CONFIG["MIN_PENGUIN_WEIGHT"] and scale_1.dead_weight != -999):
			print("{} - Scale 1 has been triggered. Heading out to ocean.".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
			print("Dead Weight: {:.3f} kg  Net Weight: {:.3f} kg".format(scale_1.dead_weight, scale_1_net))
			record_event(scale_1, scale_2)

		elif ( scale_2_net > CONFIG["MIN_PENGUIN_WEIGHT"] and scale_2.dead_weight != -999):
			print("{} - Scale 2 has been triggered. coming back from the ocean.".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
			print("Dead Weight: {:.3f} kg  Net Weight: {:.3f} kg".format(scale_2.dead_weight, scale_2_net))
			record_event(scale_1, scale_2)

		# This flag was used when the saving process was done in the background. 
		# This has not been effectively achieved but would prevent the serial buffers filling up
		reduce_weight_lists(scale_1, scale_2)

except (KeyboardInterrupt):
	save_error_file(scale_1, scale_2)
	print("\nscales.py closed by user. Goodbye")
	sys.exit()

except Exception as e:

	save_error_file(scale_1, scale_2)
	print("\nA problem occured while running the scales.py script - {}. Error: {}".format(CONFIG["SITE_NAME"], e))
	send_email_background("A problem occured while running the scales.py script - {}. Error: {}".format(CONFIG["SITE_NAME"], e))

	traceback.print_exc()
	print("Waiting for 1 hour before closing...")
	# Wait for 1 hour, system should then try and run the script again
	sleep(3600)
	sys.exit()
###############################################################################




