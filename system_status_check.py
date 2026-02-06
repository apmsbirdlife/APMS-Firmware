#!/usr/bin/python3

# This script does a system check every hour and sends an email if an alert is raised
# It also checks in with the monitor to get a status report
# This script is also called by the crontab at boot
##############################################################################################

from apms_email import email
from datetime import datetime, time, timedelta
from time import sleep, perf_counter
from vcgencmd import Vcgencmd
import os
import serial
import sys
import psutil
import subprocess
from shared_functions import *
 
###############################################################################
# Global variables dictionary
###############################################################################
now = datetime.now()
_time = now.strftime("%H:%M:%S")
day = now.strftime("%Y%m%d")
year =  now.strftime("%Y")
arduino_status_report = ""
internal_serial_object = 0
timer_val = 3
timer_start = 0
vcgencmd_object = Vcgencmd()
alerts_list = []
cpu_temp = 0
cpu_percentage = 0
memory_used_percentage = 0
sd_used_percentage = 0
usb_used_percentage = 0
scales_running = 'N'
rfid_running = 'N'
tailscale_running = 'N'
internet_on = 'N'
boot = 0
rpi_last_boot_obj = datetime(1970,1,1)
CONFIG = {}
###############################################################################



###############################################################################
# At boot, the crontab calls this script with the argument "boot"
# It is assumed the system has rebooted after losing power.
###############################################################################
def check_boot():
	
	global boot, rpi_last_boot_obj

	if len(sys.argv) == 2 and sys.argv[1] == "boot":

		# Set the boot flag
		boot = 1

		print("Raspberry Pi just booted...")
		sms("Raspberry Pi just booted...")
		
		# If the rpi has rebooted, there is a good chance power was lost and the system
		# time will be incorrect, thus first update the system time
		# Wait for the router to go online. This can be improved with code that checks when internet is available
		sleep(30)
	
		print("Updating system time. Time before update: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
		print(os.system("sudo ntpdate pool.ntp.org"))
		print("Time after update: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

		if_not_then_make(CONFIG["LOGS_PATH"])
		last_boot_file_path = os.path.join(CONFIG["LOGS_PATH"], "rpi_last_boot.txt")

		### Log the boot time. If the last_boot file does not exist, create it.
		rpi_last_boot_obj = datetime.now()
		rpi_last_boot_string = rpi_last_boot_obj.strftime('%Y-%m-%d %H:%M:%S')
		if os.path.exists(last_boot_file_path):
			with open(last_boot_file_path, 'a') as file:
				file.write(rpi_last_boot_string + '\n')
		else:	
			print ("Creating a last_boot file")
			with open(last_boot_file_path, 'w') as file:
				file.write(rpi_last_boot_string + '\n')

		print ("last_boot file updated")
###############################################################################



###############################################################################
def check_rpi_last_boot():
	
	global rpi_last_boot_obj
	
	last_boot_file_path = os.path.join(CONFIG["LOGS_PATH"], "rpi_last_boot.txt")
	
	if not os.path.exists(last_boot_file_path):
		print('rpi_last_boot.txt file not found.')
		return 1

	with open (last_boot_file_path, 'r') as file:
		# date_time_format = "%Y-%m-%d %H:%M:%S"
		rpi_last_boot_string = file.readlines()[-1].strip()
		rpi_last_boot_obj = datetime.strptime(rpi_last_boot_string, "%Y-%m-%d %H:%M:%S")
		print("Rpi Last Boot: ", rpi_last_boot_string)
##############################################################################
	


###############################################################################
# This script checks if the data was uploaded successfully, if not, it will try againn
###############################################################################
###################################################################################################################################
def check_last_data_upload ():

	busy_uploading_file_path = os.path.join(CONFIG["APMS_ABS_PATH"], 'busy_uploading')

	if os.path.exists(busy_uploading_file_path):
		print("System is currently busy uploading data to the cloud")
		return

	current_date_time_obj = datetime.now()
	upload_hour = CONFIG["UPLOAD_HOUR"] 		
	upload_hour_obj = datetime.combine(current_date_time_obj.date(), time(upload_hour, 0))

	upload_file_path = os.path.join(CONFIG["LOGS_PATH"],'last_upload.txt')
	if not os.path.exists(upload_file_path):
		print('last_upload.txt file not found.')
		return
	
	with open(upload_file_path, 'r') as file: 
		dates_times = file.readlines()
		last_upload_date_time = dates_times[-1].strip()
		last_upload_date_time_obj = datetime.strptime(last_upload_date_time, "%Y-%m-%d %H:%M:%S")
		last_upload_day_obj = last_upload_date_time_obj.date()
		current_day_obj = current_date_time_obj.date()
		
		print("Last Upload: ",last_upload_date_time)

		time_since_upload_hour = current_date_time_obj - upload_hour_obj

		# The data should have uploaded, if not, try again
		if time_since_upload_hour > timedelta(hours=1):

			time_since_last_upload = current_date_time_obj - last_upload_date_time_obj

			# Example: If upload hour is 1:00, and it is currently 4am and the data has not transfered, then
			# time_since_upload_hour is 3 and time_since_last_upload will be say 27 hours, then 
			# it will try and upload agin
			
			if time_since_last_upload > time_since_upload_hour:

				print("The last time data was uploaded to the cloud was: ", last_upload_day_obj)
				print("Running data_transfer script...")
				command = "/usr/bin/python3 /home/apms/apms/transfer_data.py >> /home/apms/logs/transfer_data.log 2>&1"
				result = subprocess.run(command, shell=True, executable="/bin/bash", cwd="/home/apms")
				if result.returncode == 0:
					print("Data succesfully uploaded")
				else:
					print("Data not succesfully uploaded")
					return 1
###############################################################################



###############################################################################
def check_cpu_temp():

	global alerts_list, cpu_temp
	try:
		cpu_temp = vcgencmd_object.measure_temp()
		print("The current CPU temperature is {} deg C".format(cpu_temp))

		if cpu_temp < CONFIG["CPU_TEMP_WARNING"]:
			print("CPU temperature OK")

		elif cpu_temp > CONFIG["CPU_TEMP_DANGER"]:
			print("Warning! CPU temperature dangerously high! An alert has been triggered")
			alerts_list.append("CPU temperature dangerously high: {}".format(cpu_temp))

		else:
			print("Warning. CPU temperature is high.")
			alerts_list.append("CPU temperature is high: {}".format(cpu_temp))

	except Exception as e:
		print("Failure during check_cpu(): {}".format(e))
		alerts_list.append("Failure during check_cpu()")
##############################################################################################




##############################################################################################
def check_cpu_load():
	global cpu_percentage
	cpu_percentage_list = psutil.cpu_percent(interval=5, percpu=True)
	cpu_percentage = max(cpu_percentage_list)
	print("CPU max load is {}%".format(cpu_percentage))
##############################################################################################



##############################################################################################
def check_throttle_state():

	'''
	These throttle states will be added to the throttle_states.txt file in the logs directory
	The user will only be notified, when it occurs for the first time since last boot.
	The user will also be notified if the thottling is still ongoing

	Throttle states:
	| 0 | Under-voltage detected |
	| 1 | Arm frequency capped |
	| 2 | Currently throttled |
	| 3 | Soft temperature limit active |
	| 16 | Under-voltage has occurred |
	| 17 | Arm frequency capped has occurred |
	| 18 | Throttling has occurred |
	| 19 | Soft temperature limit has occurred
	'''

	global alerts_list

	try:
		throttle_state = vcgencmd_object.get_throttled()

		if int(throttle_state["raw_data"],0) == 0 :
			print("No throttling")
			pass
		else:

			if throttle_state["breakdown"]["0"] == True:
				print("** CPU is currently experiencing an under voltage condition")
				alerts_list.append("** CPU is currently experiencing an under voltage condition")

			if throttle_state["breakdown"]["1"] == True:
				print("** CPU frequency is currently being capped")
				alerts_list.append("** CPU frequency is currently being capped")

			if throttle_state["breakdown"]["2"] == True:
				print("** CPU is currently being throttled")
				alerts_list.append("** CPU is currently being throttled")

			if throttle_state["breakdown"]["3"] == True:
				print("** Soft temperature limit active")
				alerts_list.append("** Soft temperature limit active")
	
			
			# Since boot


			if throttle_state["breakdown"]["16"] == True:
				print("* The CPU has previously experienced an under-voltage condition (since boot)")
				alerts_list.append("* The CPU has previously experienced an under-voltage condition (since boot)")

			if throttle_state["breakdown"]["17"] == True:
				print("* The CPU previously had it's frequency capped (since boot)")
				alerts_list.append("* The CPU previously had it's frequency capped (since boot)")

			if throttle_state["breakdown"]["18"] == True:
				print("* The CPU was previously throttled (since boot)")
				alerts_list.append("* The CPU was previously throttled (since boot)")
				

			if throttle_state["breakdown"]["19"] == True:
				print("* Soft temperature limit previously reached (since boot)")
				alerts_list.append("* Soft temperature limit previously reached (since boot)")


	except: 
		print("Failure during check_throttle_state()")
		alerts_list.append("Failure during check_throttle_state()")
##############################################################################################



##############################################################################################
def check_scales_script():
	global scales_running
	status = os.system('systemctl is-active --quiet scales')
	if status == 0:
		scales_running = 'Y'
	else:
		scales_running = 'N'
		print("* Scales not running")
		alerts_list.append("Scales not running")
##############################################################################################



##############################################################################################
# Check if the RFID script is running
def check_rfid_script():
	global rfid_running
	status = os.system('systemctl is-active --quiet rfid')
	if status == 0:
		rfid_running = 'Y'
	else:
		rfid_running = 'N'
		print("* RFID not running")
		alerts_list.append("RFID not running")
##############################################################################################



##############################################################################################
def check_tailscale():
	global tailscale_running
	status = os.system('systemctl is-active --quiet tailscaled')
	if status == 0:
		tailscale_running = 'Y'
		print("tailscale is running")
	else:
		tailscale_running = 'N'
		print("* tailscale not running")
		alerts_list.append("tailscale not running")
##############################################################################################



##############################################################################################
def check_internet():
	global internet_on
	status = test_internet()
	if status == 0:
		internet_on = 'Y'
	else:
		internet_on = 'N'
##############################################################################################



##############################################################################################
def check_sd_used():
	global sd_used_percentage
	sd_usage = psutil.disk_usage('/')
	sd_used_percentage = sd_usage[3]
	print("uSD storage used: {}%".format(sd_used_percentage))

	# stop all scripts as system will become unresponsive soon
	if sd_used_percentage > 95:

		print("SD Card too full. Stopping rfid and scales script")
		stop_rfid_scales()
		message = "SD Card almost full. RFID and Scales stopped. Please log in and clear space: {}%".format(sd_used_percentage)
		sms(message)
		alerts_list.append(message)
##############################################################################################



##############################################################################################
def check_usb_used():
	try:
		global usb_used_percentage

		if check_usb() == 0:
	
			usb_usage = psutil.disk_usage('/home/apms/flash')
			usb_used_percentage = usb_usage[3]
			print("USB drive storage used: {}%".format(usb_used_percentage))
			
			if usb_used_percentage > 90:
				print("USB Flash Drive too full.")
				alerts_list.append("USB Flash Drive almost full: {}%".format(usb_used_percentage))
	
		else:
			print("Could not determine space used on flash disk. ERROR: CUU1")
			usb_used_percentage = 0
	
	except:
		print("Could not determine space used on flash disk. ERROR: CUU2 (exception)")
##############################################################################################



##############################################################################################
def check_memory_used():
	global memory_used_percentage
	memory = psutil.virtual_memory()
	memory_used_percentage = memory.percent
	print("Memory Used: {}%".format(memory_used_percentage))
	if (memory_used_percentage > 70):
		print("Low memory")
		alerts_list.append("Low memory - Memory Used: {}%".format(memory_used_percentage))

##############################################################################################


# TEST THIS
##############################################################################################
# Reminder: The Pi starts a command with $ and ends it with a @

def check_command_from_monitor():
	print("Checking command request from Monitor")
	internal_serial_object.write('$C@'.encode())
	sleep(2)

	# Wait for the monitor to send the command, if there was one

	if internal_serial_object.in_waiting > 0:
		while (internal_serial_object.in_waiting > 0):
			rpi_command = internal_serial_object.readline().decode('ascii')
			print("Executing command: ", rpi_command)
			os.system(rpi_command)
			print("Finished execution of command")
	else:
		print("No command request")
##############################################################################################



##############################################################################################
def request_monitor_status_report():
	global alerts_list, arduino_status_report
	arduino_status_report_list = []
	print("Requesting Monitor status report...")

	try:
		internal_serial_object.write('$R@'.encode())
		sleep(4)
		
		# check to see if monitor responded
		if (internal_serial_object.in_waiting > 0):
			while (internal_serial_object.in_waiting > 0):
				line = internal_serial_object.readline().decode('ascii')
				arduino_status_report = arduino_status_report + line
			
			print(arduino_status_report)
	
		else:
			print("No data received from Monitor")
			alerts_list.append("No data received from Monitor")

	except Exception as e:
		print("Failure reading Monitor: {}".format(e))
		alerts_list.append("Failure reading Monitor: {}".format(e))
##############################################################################################



##############################################################################################
def sms(message):
	try:
		internal_serial_object.write('$Q@'.encode('ascii'))
		sleep(4)
		response = (internal_serial_object.readline().decode('ascii')).strip()
		print ("Response was: {}".format(response))
		if (response == 'ACK$Q'): # ACK$S means the Monitor acknowledged and is waiting for sms message
			print ("Sending sms")
			internal_serial_object.write(message.encode('ascii'))
			internal_serial_object.write('@'.encode('ascii'))

	except Exception as e:
		print("Failure sending sms: ",message)
##############################################################################################



##############################################################################################
# This function send the Rpi status report to the Monitor
##############################################################################################
def send_rpi_status_report():
	try:
		print("Requesting to send Raspberry Pi System Status Report.")

		internal_serial_object.write('$S@'.encode())
		sleep(4)

		response = (internal_serial_object.readline().decode('ascii')).strip()
		# print ("Response was: {}".format(response))
		if (response == 'ACK$S'): # ACK$S means the Monitor acknowledged and is waiting for report
			print ("Sending Raspberry Pi Status Report")

			# Last time the raspberry pi rebooted
			BT = rpi_last_boot_obj.strftime('%Y%m%d %H:%M')
			
			# Current "check-in" time
			CH = datetime.now().strftime('%Y%m%d %H:%M')

			message = "{}\nBT:{}\nCH:{}\nS:{}\nR:{}\nT:{}\nI:{}\nCPU:{}\nMEM:{}\nSD:{}\nUSB:{}".format(
				CONFIG["SITE_CODE"],BT,CH,scales_running,rfid_running,tailscale_running,internet_on,cpu_temp,memory_used_percentage,sd_used_percentage,usb_used_percentage)
			internal_serial_object.write((message + "@").encode())
			print(message)
			print("--------------------------------------------")

			print("Raspberry Pi System Status Report sent\n")
	
	except Exception as e:
		print("Failure sending status report: {}".format(e))
		alerts_list.append("Failure sending status report: {}".format(e))
##############################################################################################
	


##############################################################################################
def start_timer (interval_sec):
	global timer_val, timer_start
	timer_val = interval_sec
	timer_start = perf_counter();
##############################################################################################



##############################################################################################
def timer ():
	if ((perf_counter() - timer_start) > timer_val):
		return 0
	else:
		return 1
##############################################################################################



##############################################################################################
def connect_monitor ():
	try:
		global internal_serial_object
		internal_serial_object = serial.Serial(port = CONFIG["SERIAL_PORT_INTERNAL"], baudrate = CONFIG["INTERNAL_BAUD_RATE"], timeout=10)
		print("Opened serial port: {}".format(CONFIG["SERIAL_PORT_INTERNAL"]))
	except:
		print("Could not open serial port: {}".format(CONFIG["SERIAL_PORT_INTERNAL"]))
		alerts_list.append("Could not open serial port: {}".format(CONFIG["SERIAL_PORT_INTERNAL"]))
	
####################################################################################################################################



###############################################################################
def save_status_data_to_file ():
	global alerts_list, _time, day
	system_status_report = ''

	status_file_path = os.path.join(data_dir, day + '_STATUS.txt')
	# filename = day + "_STATUS.txt" 
	# print("\nSaving data to {}".format(data_dir + filename))
	print("\nSaving data to: ", status_file_path)

	# Now create the main report append all the sub reports from the different checks
	system_status_report = system_status_report + "############################################################\n"
	system_status_report = system_status_report + "Start of APMS Status Report - Date: {}	  Time: {}\n\n".format(day,_time)
	system_status_report = system_status_report + "############################################################\n"

	if (boot == 1):
		system_status_report = system_status_report + "System just booted\n"
	
	rpi_last_boot_string = rpi_last_boot_obj.strftime('%Y-%m-%d %H:%M:%S')

	system_status_report = system_status_report + "Site Name: {}\n".format(CONFIG["SITE_NAME"])
	system_status_report = system_status_report + "CPU temperature: {} deg C\n".format(cpu_temp)
	system_status_report = system_status_report + "CPU load: {} %\n".format(cpu_percentage)
	system_status_report = system_status_report + "SD storage used: {} %\n".format(sd_used_percentage)
	system_status_report = system_status_report + "USB drive storage used: {} %\n".format(usb_used_percentage)
	system_status_report = system_status_report + "Memory used: {} %\n".format(memory_used_percentage)
	system_status_report = system_status_report + "Raspberry Pi last boot: {}\n".format(rpi_last_boot_string)
	
	if (alerts_list):
		alert_message = "APMS Alert triggered for {}: Please see below: \n{}".format(CONFIG["SITE_NAME"], alerts_list)
		print(alert_message)
		email(alert_message)
		sms(alert_message)
		system_status_report = system_status_report + "ATTENTION! The following system alerts have been triggered:\n"
		for alert in alerts_list:
			system_status_report = system_status_report + "{}".format(alert) + " \n"

	else:
		print("---No alerts were triggered---\n")
		system_status_report = system_status_report + "No alerts were triggered\n"

	system_status_report = system_status_report	+  arduino_status_report

	now = datetime.now()
	_time = now.strftime("%H:%M:%S")
	day = now.strftime("%Y%m%d")
	system_status_report = system_status_report + "End of APMS Status Report - Date: {}	  Time: {}\n".format(day,_time)
	system_status_report = system_status_report + "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n\n"
	
	with open(status_file_path, 'a+') as file:
		file.write(system_status_report)
###############################################################################





###############################################################################
def stop_rfid_scales ():
	print("Stopping the scales script")
	subprocess.run(["sudo", "systemctl", "stop", "scales"],text=True)  # Ensures the output is returned as a string)
	print("Stopping the rfid script")
	subprocess.run(["sudo", "systemctl", "stop", "rfid"],text=True)  # Ensures the output is returned as a string)
			



###############################################################################
# Run the update_system_time.py script to update the system time
###############################################################################
def update_system_time():
	command = "/usr/bin/python3 /home/apms/apms/update_system_time.py >> /home/apms/logs/update_time.log 2>&1"
	result = subprocess.run(command, shell=True, executable="/bin/bash", cwd="/home/apms")
	if result.returncode == 0:
		print("Time succesfully updated")
	else:
		print("Time not succesfully uploaded")




###############################################################################
# START 
###############################################################################
CONFIG = load_config_file()

# Get the name of the data directory and try to create it. 
# If it exists, give an error message and exit
data_dir = os.path.join(CONFIG["DATA_PATH"], year, day)

if os.path.isdir(data_dir):
	print("Data directory found")
else:
	os.makedirs(data_dir)
	print("Data directory created. {}".format(data_dir))

print ("\n############################################################")
print (  "############         APMS Status Report          ###########")
print (  "############ Date: {}	  Time: {} ###########".format(day,_time))
print (  "############################################################\n")

connect_monitor()
check_boot()
check_rpi_last_boot()
check_last_data_upload()
check_cpu_temp()
check_cpu_load()
check_memory_used()
check_sd_used()
check_usb_used()
check_throttle_state()
check_scales_script()
check_rfid_script()
check_tailscale()
check_internet()
check_command_from_monitor()
request_monitor_status_report()
send_rpi_status_report()
save_status_data_to_file()

now = datetime.now()
_time = now.strftime("%H:%M:%S")
day = now.strftime("%Y%m%d")
print ("\n############################################################")
print (  "############      End of APMS Status Report      ###########")
print (  "############ Date: {}	  Time: {} ###########".format(day,_time))
print (  "############################################################\n")

sys.exit()

###############################################################################
# END 
###############################################################################

