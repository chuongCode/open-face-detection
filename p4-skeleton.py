#!/usr/bin/env python 

from subprocess import Popen, DEVNULL
import shlex, os, errno, time, glob

#Constants for later use
of2_verbose = False
temp_output = "of2_out"
temp_output_file = temp_output + '.csv'
landmark_count = 68

#This line finds the openface software
#If you're getting an error here, make sure this file is in the same folder as your openface installation
exe = ([exe for exe in glob.glob("./**/FeatureExtraction", recursive=True) if os.path.isfile(exe)]+[exe for exe in glob.glob(".\\**\\FeatureExtraction.exe", recursive=True)])[0]

#Clean up the temp file from a previous run, if it exists
try:
	os.remove(temp_output_file)
except OSError as e: 
	if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
		raise # re-raise exception if a different error occurred

#These lines write the command to run openface with the correct options
command = shlex.split(" -device 0 -out_dir . -pose -2Dfp -of "+temp_output)
command.insert(0, exe)

#This line starts openface
of2 = Popen(command, stdin=DEVNULL, stdout=(None if of2_verbose else DEVNULL), stderr=DEVNULL)

#This loop waits until openface has actually started, as it can take some time to start producing output
while not os.path.exists(temp_output_file):
	time.sleep(.5)

#Openface saves info to a file, and we open that file here
data = open(temp_output_file,'r')

# Initialize variables to store the previous frame's angles
accumulated_pitch_diff = 0.0
accumulated_yaw_diff = 0.0
accumulated_roll_diff = 0.0
start_time = None
gesture_detection_window = 0.75

# Thresholds for gesture detection
pitch_threshold_for_yes = 0.8
yaw_threshold_for_no = 1
roll_threshold_for_indian_nod = 1

previous_pitch = None
previous_yaw = None
previous_roll = None

#This loop repeats while openface is still running
#Inside the loop, we read from the file that openface outputs to and check to see if there's anything new
#We handle the data if there is any, and wait otherwise
while(of2.poll() == None):
	line = data.readline().strip()
	
	if(line != ""):
		try:
			#Parse the line and save the useful values
			of_values = [float(v) for v in line.split(', ')]
			timestamp, confidence, success = of_values[2:5]
			pitch, yaw, roll = of_values[8:11]
			# landmarks = []
			# for i in range(11,11+landmark_count):
			# 	landmarks.append((of_values[i],of_values[i+landmark_count]))

			# If this is the first iteration, initialize the previous variables and skip the rest of the loop
			if previous_pitch is None or previous_yaw is None or previous_roll is None:
				previous_pitch = pitch
				previous_yaw = yaw
				previous_roll = roll
				start_time = timestamp
				continue  # Skip the rest of this loop iteration

			# Calculate the difference in angles from the previous frame
			pitch_diff = abs(pitch - previous_pitch)
			yaw_diff = abs(yaw - previous_yaw)
			roll_diff = abs(roll - previous_roll)

			# Accumulate differences over the gesture detection window
			accumulated_pitch_diff += pitch_diff
			accumulated_yaw_diff += yaw_diff
			accumulated_roll_diff += roll_diff

			# Update previous angles for the next iteration
			previous_pitch = pitch
			previous_yaw = yaw
			previous_roll = roll
			
			# Check if the current timestamp exceeds the gesture detection window
			if timestamp - start_time >= gesture_detection_window:

				if accumulated_pitch_diff > pitch_threshold_for_yes:
					print("Yes")
				elif accumulated_yaw_diff > yaw_threshold_for_no:
					print("No")
				elif accumulated_roll_diff > roll_threshold_for_indian_nod:
					print("Indian Nod")

				# Resetting the accumulated differences and the start time for the next window
				accumulated_pitch_diff = 0.0
				accumulated_yaw_diff = 0.0
				accumulated_roll_diff = 0.0
				start_time = timestamp  # Move this inside the if condition to correctly reset after processing a window


		except ValueError:
			#This exception handles the header line
			continue
			
		#********************************************
		# Most, maybe all, of your code will go here
		#********************************************

		# print("time:", timestamp, "\tpitch:", pitch, "\tyaw:", yaw, "\troll:", roll)
	else:
		time.sleep(.01)
	
#Reminder: press 'q' to exit openface

print("Program ended")

data.close()