###############################################################################
# This script is used to update the system time
# The script first checks the scales_busy file to see if a scale event is happening
# This script is run by the crontab, once a week. 
###############################################################################
import time
import os
import sys
from datetime import datetime
from shared_functions import *

###############################################################################
# Global variables dictionary
###############################################################################
wait_time_min = 10
CONFIG = load_config_file()

scales_busy_file_path = os.path.join(CONFIG["APMS_ABS_PATH"], 'scales_busy')
print("Current system time: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
try:

	print ("Checking if scales are busy...")

	while(True):

		# check if scales_busy file exists
		if os.path.isfile(scales_busy_file_path) == 1:

			print("Scales are busy, waiting for them to finish")

			# wait for scales_busy file to be deleted
			stopwatch = 0
			while os.path.isfile(scales_busy_file_path) == 1:
				time.sleep(1)
				stopwatch = stopwatch + 1
				print(stopwatch, end=', ', flush=True)

			print("\nScales are no longer busy. Waiting {} minutes before updating time...".format(wait_time_min))

		else:
			print("Scales are not busy. Waiting {} minutes before updating time...".format(wait_time_min))


		# Now we make sure there are no scale triggers for 10 minutes.
		# This ensures that if the clock was shifted back by a few minutes, it will not overlap with any penguins crossing

		wait_time_sec = wait_time_min * 60
		for i in range(0,wait_time_sec):
			if os.path.isfile(scales_busy_file_path) == 1:
				print("Scales triggered...")
				break
			else:
				time.sleep(1)
				if i == (wait_time_sec-1):
					print("Scales have been empty for at least {} minutes. Updating time".format(wait_time_min))
					print("Time before update: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
					os.system("sudo ntpdate pool.ntp.org")
					
					if os.path.isfile(scales_busy_file_path == 1):
						print("Scales triggered during time update")
					else:
						print("System time updated succesfully")

					print("New system time: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
					sys.exit()

except (KeyboardInterrupt):
	print("Exiting. Thank you")
	sys.exit()



