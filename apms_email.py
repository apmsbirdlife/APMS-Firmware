#########################################################################################
# This script can be used from the command line or in another python script. 
# To use from the command line, please see below for examples
# Example 1: python3 apms_email.py "This is the body of the email"
# Example 2: python3 apms_email.py "This is the body of the email", attachment.zip
#########################################################################################
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sys
import json
from shared_functions import *

###############################################################################
# Global dictionary variable holding all constants
###############################################################################
CONFIG = {}
#########################################################################################


#########################################################################################
def email (message = "NO MESSAGE", attachment_abs_path = 0):

	try:
		CONFIG = load_config_file()

		fromaddr = CONFIG["EMAIL_ADDRESS"]
		toaddr = CONFIG["EMAIL_ADDRESS_ADMIN"]

		# instance of MIMEMultipart
		msg = MIMEMultipart()

		# storing the senders email address  
		msg['From'] = fromaddr
		  
		# storing the receivers email address 
		msg['To'] = toaddr
		  
		# storing the subject 
		msg['Subject'] = "APMS Data"

		# attach the message with the msg instance
		msg.attach(MIMEText(message, 'plain'))

		if message == "NO MESSAGE":
			print (message)
			print("Sending email without message")

		if attachment_abs_path:
			print("Sending attachment: {}".format(attachment_abs_path))
			attachment = open(attachment_abs_path, "rb")
			# instance of MIMEBase and named as p
			p = MIMEBase('application', 'octet-stream')
			# To change the payload into encoded form
			p.set_payload((attachment).read())
			# encode into base64
			encoders.encode_base64(p)
			p.add_header('Content-Disposition', "attachment; filename= %s" % attachment_abs_path)
			# attach the instance 'p' to instance 'msg'
			msg.attach(p)
		else:
			print("Sending email without attachment")  

		# creates SMTP session
		s = smtplib.SMTP('smtp.gmail.com', 587)  
		# start TLS for security
		s.starttls()
		# Authentication
		s.login(fromaddr, CONFIG["EMAIL_PASSWORD"])
		# Converts the Multipart msg into a string
		text = msg.as_string()
		# sending the mail
		s.sendmail(fromaddr, toaddr, text)
		# terminating the session
		s.quit()
		print("email sent")  
		return 1
	
	except:
		print("Could not send email")

#########################################################################################



#########################################################################################
if __name__ == "__main__":

	if len(sys.argv) == 3:
		#print("there are 2 arguments")
		message = sys.argv[1]
		attachment_abs_path = sys.argv[2]
		email(message = message, attachment_abs_path = attachment_abs_path)
		
	elif len(sys.argv) == 2:
		#print("there is 1 argument")
		message = sys.argv[1]
		email(message = message)

	else:
		print("Invalid arguments")
		sys.exit()

	print("Script finished at: {}".format(datetime.now().strftime("%H:%M:%S %Y-%m-%d")))
	sys.exit()
#########################################################################################
