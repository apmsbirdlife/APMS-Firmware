#!/bin/bash
pymcuprog write -f ./build/arduino.megaavr.nona4809/system_monitor.ino.hex -d atmega4809 -t uart -u /dev/ttyAMA1 --erase