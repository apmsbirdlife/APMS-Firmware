APMS (Automated Penguin Monitoring System)

This repository contains the software needed to run the APMS (Automated Penguin Monitoring System).

The system consists of two scales that send continuous weight readings at 100Hz to a Raspberry Pi 4. There is also a Monitoring circuit, consisting of common off-the-shelf components, to ease future debugging and upgrading. The system is connected to an RFID detection system, designed by BioMark. The Biomark system sends out data via the serial port when an RFID tag was detected. When a penguin walks over the scales, the data is recorded in a CSV file. Every night, the data is uploaded to the cloud. (AWS S3).