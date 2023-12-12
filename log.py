###############################################################################
# This script is used to log any work done on the APMS system.
###############################################################################
# Imports
import os
from datetime import datetime
import sys
import json
import shutil
from shared_functions import *

###############################################################################
# Global variables dictionary
###############################################################################
CONFIG = {}
##############################################################################



##############################################################################
def main ():

	global CONFIG

	# Load config.json
	CONFIG = load_config_file()


	now_obj = datetime.now()
	now_str = now_obj.strftime("%Y%m%d%H%M%S")
	
	log_file_path = os.path.join(CONFIG["LOGS_PATH"], 'log.txt')
	input_format = "%Y/%m/%d %H:%M"

	print("Welcome to the APMS Logging Script")
	print("You can use CTRL+C to exit without saving the entry")
	print("Please enter a date and time for the entry (Example: 2023/10/23 10:05) or press ENTER to use the current time.")

	while True:
		response = input()
		if (response == ''):
			date_time_obj = datetime.now()
			break
		else:
			date_time_obj = datetime.strptime(response, input_format)
			break


	timestamp = date_time_obj.strftime(input_format)

	print("Please enter a description of the work done: ")
	description = input()

	log_entry = "{} - {}\n".format(timestamp, description)

	print("\nThe following entry will be added to the log file.\n")
	print(log_entry)
	print("Press ENTER to continue...")
	while True:
		response = input()
		if response == '':
			break
		else:
			print("Please press ENTER to save or CTRL+C to quit without saving")

	
	if os.path.exists(log_file_path):
		print("Backing up existing log file...")
		log_backup_dir_path = os.path.join(CONFIG["LOGS_PATH"], 'backup') 
		if_not_then_make(log_backup_dir_path)
		log_backup_filename = "{}_log_backup.txt".format(now_str)
		log_backup_file_path = os.path.join(log_backup_dir_path, log_backup_filename)
		shutil.copy(log_file_path, log_backup_file_path)
		print("Done backing up log file")

	with open(log_file_path, "a") as log_file:
		log_file.write(log_entry)


	print("Entry logged. \nThank you. Have a nice day.")
##############################################################################



#############################################################################
def if_not_then_make (path):
    if not os.path.exists(path):
        os.makedirs(path)
##############################################################################




##############################################################################
if __name__ == "__main__":

	try:
		main()

	except (KeyboardInterrupt):
		print("\nClosing log.py without saving. \nThank you. Have a nice day.")
		sys.exit()

	except Exception as e:
		print("An error occured: ", e)
		print("Closing...")
##############################################################################