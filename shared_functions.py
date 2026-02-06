import os
import json
from time import sleep

###############################################################################
# Global dictionary variable holding all constants
###############################################################################
CONFIG = {}

###############################################################################
# This function loads all the relevant constants from the config.JSON file.
###############################################################################
def load_config_file ():
	global CONFIG
	with open('/home/apms/apms/config.json', 'r') as config_file:
		config = json.load(config_file)
		CONFIG.update(config)
		return CONFIG
###############################################################################


###############################################################################
# Check if Flash Drive is mounted, if not, mount it
###############################################################################
def check_usb ():
	print("Checking USB Flash Drive...")
	try:
		if (os.path.ismount(CONFIG["USB_PATH"])): # returns 1 if mounted and all good
			print("USB drive partition {} mounted to {}".format(CONFIG["USB_PARTITION"],CONFIG["USB_PATH"]))
			return 0
		else:
			print("USB drive not mounted. Attempting to mount {} to {}".format(CONFIG["USB_PARTITION"],CONFIG["USB_PATH"]))
			if (mount_usb() == 0):
				return 0
			else:
				return 1
	
	except Exception as e:
		print(e)
###############################################################################


###############################################################################
# Mount the Flash Drive
###############################################################################
def mount_usb():
	try:
		# First create a mount point if it does not already exist
		try:
			os.makedirs(CONFIG["USB_PATH"])
		except FileExistsError:
			pass
		else:
			print("Mount point created")

		# Now try and mount
		os.system("sudo mount {} {}".format(CONFIG["USB_PARTITION"],CONFIG["USB_PATH"]))
		
		# check that usb is indeed mounted
		if (os.path.ismount(CONFIG["USB_PATH"])):
			print("USB drive partition {} succesfully mounted to {}".format(CONFIG["USB_PARTITION"],CONFIG["USB_PATH"]))
			return 0
		else:
			print("USB Drive not mounted")
			return 1

	except Exception as e:
		print("There was a problem mounting the USB drive: ".format(e))
		return 1
###############################################################################


###############################################################################
# Check Internet Connection
###############################################################################
def test_internet():
	print("Testing internet connection...")
	if (ping_internet() == 0):
		print("Device is connected to the internet")
		return 0
	else:
		print("Device is not connected to the internet. Checking connection to the router...")
		if (ping_router() == 0):
			print("Device is connected to the router but the router does not have internet access.")
			return 1
		else:
			print("Device not connected to the router.")
			return 1
###############################################################################

###############################################################################
# Ping Google
###############################################################################
def ping_internet ():
	print("ping Google at 8.8.8.8")
	internet_ping_response = os.system("ping -c 1 8.8.8.8 > /dev/null 2>&1")
	sleep(5)
	if internet_ping_response == 0:
		return 0
	else:
		return 1
###############################################################################



###############################################################################
# Ping the router
###############################################################################
def ping_router():
	router_ping_response = os.system("ping -c 1 192.168.1.1 > /dev/null 2>&1")
	sleep(5)
	if router_ping_response == 0:
		return 0		
	else:
		return 1		
###############################################################################



###############################################################################
def if_not_then_make (path):
    if not os.path.exists(path):
        os.makedirs(path)
###############################################################################