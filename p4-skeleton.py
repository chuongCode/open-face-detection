#!/usr/bin/env python 

from subprocess import Popen, DEVNULL
import shlex, os, errno, time, glob
from math import dist

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

# Initialize variables to store the current expression state and cooldown period for gesture detection
# This is for the purpose of making sure the cam doesn't flag going back to neutral face state as another detection of smiling or surprise
expression_state = 'neutral'
cooldown_start = None
cooldown_period = 2.0

# Initialize variables to store the amount of change in angles and distances over the gesture detection window
accumulated_pitch_diff = 0.0
accumulated_yaw_diff = 0.0
accumulated_roll_diff = 0.0

accumulated_smile_change = 0.0
accumulated_surprise_mouth_change = 0.0
accumulated_surprise_eyebrow_change = 0.0

start_time = None
expression_start_time = None
gesture_detection_window = 0.8
expression_detection_window = 0.2

# Thresholds for gesture detection
pitch_threshold_for_yes = 0.8
yaw_threshold_for_no = 1
roll_threshold_for_indian_nod = 1

# Thresholds for smile and surprise
smile_threshold = 20
surprise_threshold_eyebrows = 8
surprise_threshold_mouth = 20

previous_pitch = None
previous_yaw = None
previous_roll = None
previous_lip_distance = None
previous_mouth_open_distance = None
previous_eyebrow_distance = None

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
			landmarks = []
			for i in range(11,11+landmark_count):
				landmarks.append((of_values[i],of_values[i+landmark_count]))

			if cooldown_start is not None and (timestamp - cooldown_start < cooldown_period):
				continue

			# If this is the first iteration, initialize the previous variables and skip the rest of the loop
			if previous_pitch is None or previous_yaw is None or previous_roll is None:
				previous_pitch = pitch
				previous_yaw = yaw
				previous_roll = roll
				start_time = timestamp
				expression_start_time = timestamp
				continue  # Skip the rest of this loop iteration

			lip_distance = dist(landmarks[48], landmarks[54])
			eyebrow_distance = (dist(landmarks[19], landmarks[51]) + dist(landmarks[24], landmarks[51])) / 2  # Average eyebrow height
			mouth_open_distance = dist(landmarks[51], landmarks[57])

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

			# Calculate changes in distances if previous distances were set
			if previous_lip_distance is not None and previous_mouth_open_distance is not None and previous_eyebrow_distance is not None:
				accumulated_smile_change += abs(lip_distance - previous_lip_distance)
				accumulated_surprise_mouth_change += abs(mouth_open_distance - previous_mouth_open_distance)
				accumulated_surprise_eyebrow_change += abs(eyebrow_distance - previous_eyebrow_distance)

			previous_lip_distance = lip_distance
			previous_mouth_open_distance = mouth_open_distance
			previous_eyebrow_distance = eyebrow_distance
			
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

				start_time = timestamp

			# Check if the current timestamp exceeds the expression detection window
			if timestamp - expression_start_time >= expression_detection_window:
				# Check for smile and surprise expressions
				detected_expression = None
				if accumulated_smile_change > smile_threshold:
					detected_expression = 'smiley'
				elif accumulated_surprise_eyebrow_change > surprise_threshold_eyebrows and accumulated_surprise_mouth_change > surprise_threshold_mouth:
					detected_expression = 'surprised'

				# If an expression was detected, update the expression state and start the cooldown period
				if detected_expression is not None and detected_expression != expression_state:
					print(f"You look prototypically {detected_expression.capitalize()}!")
					expression_state = detected_expression
					cooldown_start = timestamp
				elif detected_expression is None and expression_state != 'neutral':
					expression_state = 'neutral'

				# Resetting the accumulated differences and the start time for the next window
				accumulated_smile_change = 0.0
				accumulated_surprise_mouth_change = 0.0
				accumulated_surprise_eyebrow_change = 0.0

				expression_start_time = timestamp

			# print(f"Lip Distance: {lip_distance:.2f}, Eyebrow Raise (L/R): {eyebrow_raise_left:.2f}/{eyebrow_raise_right:.2f}, Mouth Open: {mouth_open_distance:.2f}")


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