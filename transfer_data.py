###############################################################################
# This script sends the data, log files and status report to the cloud (AWS S3)
###############################################################################

import shutil
from apms_email import email
import os
import sys
from time import sleep
from datetime import datetime, timedelta
import subprocess
import json
from shared_functions import *

###############################################################################
# Global dictionary variable holding all constants
###############################################################################
CONFIG = {}


###############################################################################
# This function backs up the data to the flash drive. Returns 0 if succesfull
###############################################################################
def data_transfer_USB():
	print ("Backing up to USB flash drive...")
	try:
		os.system("sudo rsync -av {} {} > /dev/null 2>&1".format(CONFIG["DATA_PATH"],CONFIG["USB_PATH"]))
		return 0

	except Exception as e:
		print("There was a problem backing up data to the USB flash drive. The following error message was received: {}".format(e))
		return 1
###############################################################################



###############################################################################
def upload_log_file():

	file_path = os.path.join(CONFIG["LOGS_PATH"], 'log.txt')
	backup_dir = os.path.join(CONFIG["LOGS_PATH"], 'backup')

	# Sync the log backup files
	if os.path.exists(backup_dir):
		print ("Copying log backup files")
		aws_s3_data_path = CONFIG["AWS_S3_DATA_PATH"] + 'log_backup'
		if upload_to_cloud(backup_dir, aws_s3_data_path) == 1:
			print("Could not upload log backup files to the cloud")
		else:
			print("Uploaded log backup files to the cloud succesfully")
	else:
		print("No log backup directory to upload")


	if os.path.exists(file_path):
		print("Uploading current log file...")

		command = "aws s3 cp {} {}".format(file_path, CONFIG["AWS_S3_DATA_PATH"])
		
		print(command)

		completed_process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		exit_code = completed_process.returncode
		
		if (exit_code == 0):
			print("Uploaded current log file to the cloud succesfully")
			return 0
		else:
			print("Could not upload current log file to the cloud")
			return 1
	else:
		print("No current log file found")
		return 1
##############################################################################################################################################################



###############################################################################
def get_last_upload_obj ():
	
	file_path = os.path.join(CONFIG["LOGS_PATH"], 'last_upload.txt')
	date_format = "%Y-%m-%d"

	try:
		with open(file_path, 'r') as file:
			dates = file.readlines()
			last_upload_date = dates[-1].strip()
			last_upload_day = last_upload_date[0:10]
			last_upload_day_obj = datetime.strptime(last_upload_day, date_format)
			return last_upload_day_obj
		
	except Exception as e:
		return 1
###############################################################################



###############################################################################
def data_transfer_remote ():

	today_obj = datetime.now()
	last_upload_day_obj = get_last_upload_obj()

	if last_upload_day_obj == 1:
		print("Could not read last_upload.txt - Transferring yesterday's data")
		last_upload_day_obj = today_obj - timedelta(days=1)

	day_obj_list = get_day_object_list(last_upload_day_obj, today_obj)
	
	print("Uploading data for the following days:")
	for day_obj in day_obj_list:
		print(day_obj.strftime("%Y%m%d"))

	for day_obj in day_obj_list:

		day = day_obj.strftime("%Y%m%d")
		year = day[0:4]

		print("Sending data remotely for: {}...".format(day))

		data_path = os.path.join(CONFIG["DATA_PATH"], year, day)
		aws_s3_data_path = CONFIG["AWS_S3_DATA_PATH"] + year + '/' + day + '/'
			
		# If the main data directory exists, upload it to the cloud
		if (os.path.exists(data_path)):
			
			if upload_to_cloud(data_path, aws_s3_data_path) == 1:
				print("Could not upload data to the cloud")
				return 1
			else:
				print("Uploaded data to the cloud succesfully")
		else:
			print ("No data to upload to the cloud")
	return 0
##############################################################################################################################################################



##############################################################################
def upload_to_cloud (local_path, remote_path):

	# print("path: ", main_data_path)
	# print("path aws: ", aws_s3_main_data_path)
	
	if os.path.exists(local_path):
			
		print("local path: ", local_path)
		print("remote path: ", remote_path)

		command = "/usr/bin/aws s3 sync {} {}".format(local_path, remote_path)
		completed_process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		exit_code = completed_process.returncode
		stdout = completed_process.stdout
		stderr = completed_process.stderr

		if (exit_code == 0):
			print("Remote upload to {} successful".format(remote_path))
			return 0
				
		else:
			print("There was a problem uploading the data to the cloud. aws sync exit code: ", exit_code)
			print("Output:")
			print(completed_process.stdout)
			print("Error:")
			print(completed_process.stderr)
			return 1
##############################################################################



##############################################################################
def get_day_object_list (day_obj_start, day_obj_end):

	day_obj_list = []
	
	one_day = timedelta(days=1)

	day_obj = day_obj_start
	while (day_obj.date() <= day_obj_end.date()):

		# print("start ",day_obj_start)
		# print("end ",day_obj_end)
		day_obj_list.append(day_obj)
		day_obj = day_obj + one_day
		
	day_obj_list = sorted(day_obj_list)
	return day_obj_list
##############################################################################



##############################################################################
def save_upload_timestamp ():

	upload_file_path = os.path.join(CONFIG["LOGS_PATH"] + 'last_upload.txt')

	now_obj = datetime.now()
	last_upload_timestamp = now_obj.strftime('%Y-%m-%d %H:%M:%S')

	with open(upload_file_path, 'a') as file:
		file.write(last_upload_timestamp + '\n')
##############################################################################



###############################################################################
# START 
###############################################################################
os.system("touch ~/apms/busy_uploading")

try:
	print("\n")
	print ("##################################################################")
	print ("Data Transfer Started		",datetime.now().strftime("%d-%m-%Y - %H:%M:%S"))
	print ("##################################################################")

	# Load config.json
	CONFIG = load_config_file()

	# This is the email message that will be added to during the script
	email_message = "APMS Data Transfer Report for: {} \n".format(CONFIG["SITE_NAME"])

	if (CONFIG["UPLOAD"] == 0):
		print ("--------- Configuration file set to not upload or back up to USB -------")
		print("Goodbye")
		sys.exit()

	if (check_usb() == 0):
		if (data_transfer_USB() == 0):
			message = "Data succesfully copied to the USB flash drive\n"
			print (message)
			email_message = email_message + message
		else:
			message = "Flash drive mounted but data could not be copied.\n"
			print (message)
			email_message = email_message + message
	else:
		message = "Flash drive could not be mounted\n"
		print (message)
		email_message = email_message + message


	# If there is an internet connection
	if (test_internet() == 0):

		if (upload_log_file() == 0):
			message = "Log file for {} succesfully transfered to the cloud\n".format(CONFIG["SITE_NAME"])
			email_message = email_message + message

		if (data_transfer_remote() == 0):
			message = "Data for {} succesfully transfered to the cloud\n".format(CONFIG["SITE_NAME"])
			save_upload_timestamp()
			print (message)
			email_message = email_message + message

		else:
			message = "System is connected to the internet but data transfer to the cloud failed.\n"
			print (message)
			email_message = email_message + message
	
		print("Email Message:\n", email_message)
		email(email_message)

	else:
		message = "No connection to the internet. Upload to the cloud failed\n"
		print (message)

	os.system("rm ~/apms/busy_uploading")
	print ("##################################################################")
	print ("Data Transfer Finished		",datetime.now().strftime("%d-%m-%Y - %H:%M:%S"))
	print ("##################################################################")
	sys.exit()
	

except (KeyboardInterrupt):
	print("\nClosing transfer_data.py --- {}".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
	os.system("rm ~/apms/busy_uploading")
	sys.exit()

except Exception as e:
	print("An exception occurred: {}".format(str(e)))
	email("A problem occured while running the transfer_data.py script on {}. Error: {}".format(CONFIG["SITE_NAME"], e))
	os.system("rm ~/apms/busy_uploading")
	sys.exit()

###############################################################################
# END 
###############################################################################