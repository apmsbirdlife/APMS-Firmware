import os
import sys
from datetime import datetime

print("Updating system time. Time before update: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
os.system("sudo ntpdate pool.ntp.org")
print("Time after update: ", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

