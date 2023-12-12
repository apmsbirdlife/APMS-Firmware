import serial
import serial.tools.list_ports
import time
import sys
import os
import json
from datetime import date, datetime
from apms_email import email
from shared_functions import *

###############################################################################
# Global variables dictionary
###############################################################################
serial_port_rfid = 0
rfid_serial_object = 0
rfid_running = False
CONFIG = {}
###############################################################################



###############################################################################
def setup ():
	global rfid_serial_object
	global rfid_running

	get_serial_port()

	try:
		rfid_serial_object = serial.Serial(port = serial_port_rfid, baudrate = CONFIG["RFID_BAUD_RATE"], timeout=5)
		rfid_running = True
		print("Connected to RFID on {}".format(serial_port_rfid))
	except:
		print("There was a problem connecting to the RFID device on {}".format(serial_port_rfid))
		email("There was a problem connecting to the RFID device on {}".format(serial_port_rfid))
		rfid_running = False
		time.sleep(600)
###############################################################################
		


###############################################################################
def main ():

	print("Waiting for RFID tag...")
	while True:
	
		if rfid_running == True:
			try:
				tag = rfid_serial_object.readline().decode('utf-8')
				now = datetime.now()
				day = now.strftime("%Y%m%d")
				year = now.strftime("%Y")
				timestamp = now.timestamp()
				filename = "R" + day + now.strftime("%H%M%S") + CONFIG["SITE_CODE"] + ".csv" 

				if (tag.startswith("TAG")):
					# example: 989.001004377833
					tag_number = tag[-18:]
					print("Tag Number: {}".format(tag))
					try:
						data_dir = os.path.join(CONFIG["DATA_PATH"], year, day, 'rfid')
						os.makedirs(data_dir)
					except FileExistsError:
						pass
					else:
						print("RFID data directory created")

					filename_with_path = os.path.join(data_dir, filename)
					print ("Saving data to {}".format(filename_with_path))
					save_to_file (filename_with_path,timestamp,tag)

			except (KeyboardInterrupt):
				print("\nClosing rfid.py --- {}".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
				sys.exit()

			except Exception as e:
				print ("Could not decode BioMark message: {}".format(e))
		# If rfid_running is False, try and connect again
		else:
			setup()
###############################################################################



###############################################################################
def save_to_file (filename_with_path,timestamp,tag):
	try:
		with open(filename_with_path, 'w') as file:
			file.write( "%.3f, %s \n" % (timestamp,tag))
	except:
		print("Error saving rfid data to file")        
	else:
		print("Data saved succesfully\n")
###############################################################################



################################################################################
def get_serial_port ():
	global serial_port_rfid
	print ("Serial Converter SN: ", CONFIG["RFID_SERIAL_NUMBER"])    
	ports = serial.tools.list_ports.comports()
	for p in ports:
		if (p.serial_number == CONFIG["RFID_SERIAL_NUMBER"]):
			print("Serial port for RFID is {}".format(p.device)) 
			serial_port_rfid = p.device
################################################################################



###############################################################################
# Main
################################################################################
print("Starting rfid.py {}".format(datetime.now().strftime("%H:%M:%S %Y-%m-%d")))
CONFIG = load_config_file()
setup()
main()
###############################################################################
