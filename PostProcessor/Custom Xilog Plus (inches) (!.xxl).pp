+ =======================================
+ ---
+ Version 1.1
+
+ Edited to work with SCM Pratix S12 via Xilog3
+ Bo Morin / Bluestone Woodwork / 2025
+ NOTES: 
+ Our machine uses MM for speed and feed rates but inches for 
+ dimensions and geometry.  ¯\_(ツ)_/¯
+
+ For this reason, the feed rates are
+ given a multiplier of 24.5 to convert them from inches
+ in Aspire to MM in the output file(s)
+ 
+ Z Axis and Y Axis coordinates are given a -1 multiplier to reverse 
+ the polarity to match our particular machine setup. 
+
+ XBLOWER E=0# makes sure the air blower stays on during the program.
+
+ "PARK" Sends the carriage home at the end of the file.
+
+ ---
+ =======================================

POST_NAME = "Custom Xilog Plus Arcs(inches) (*.xxl)"

FILE_EXTENSION = "xxl"

UNITS = "INCHES"

+------------------------------------------------
+ RAPID_PLUNGE_TO_STARTZ = "NO"
+------------------------------------------------

+------------------------------------------------
+    Line terminating characters
+------------------------------------------------

LINE_ENDING = "[13][10]"

+================================================
+
+    Formating for variables
+
+================================================

VAR CUT_RATE = [FC|A|V|1.0|24.5]
VAR PLUNGE_RATE = [FP|A|V|1.0|24.5]
VAR X_POSITION = [X|A|X|1.4]
VAR Y_POSITION = [Y|A|Y|1.4|-1]
VAR Z_POSITION = [Z|A|Z|1.4|-1]
VAR ARC_CENTRE_I_ABS_POSITION = [IA|A|I|1.4]
VAR ARC_CENTRE_J_ABS_POSITION = [JA|A|J|1.4|-1]
VAR TOOL_NUMBER = [T|A|T|1.0]
VAR SPINDLE_SPEED = [S|A|S|1.0]
VAR FEED_RATE = [F|A|V|1.0|24.5]
VAR SAFE_Z_HEIGHT = [SAFEZ|A|X|1.4|-1]
+================================================
+
+    Block definitions for toolpath output
+
+================================================

+---------------------------------------------------
+  Commands output at the start of the file
+---------------------------------------------------

begin HEADER

"H DX[XMAX] DY[YMAX] DZ[ZLENGTH] -AD R99 *IN /DEF"
"; CREATED AT [DATE] [TIME]"
"; TOOLS [TOOLS_USED]"
"; FILE NOTES: [FILE_NOTES]"
"; ********** BEGIN PROGRAM **********"
"F=1"
"XBLOWER E=0# T=[T]"
"C=0"
+---------------------------------------------------
+  Commands output at toolchange
+---------------------------------------------------
+---------------------------------------------------
begin TOOLCHANGE
+ "XBLOWER E=0# T=[T] ;TOOL CHANGE"
+ "C=0"
+ "G0 [X] [Y] [Z] [T] [S]; "
+
+---------------------------------------------------

"; ********** TOOL CHANGE [TOOLNAME] # [T] ************"

+---------------------------------------------------
+  Commands output for rapid moves
+---------------------------------------------------

begin RAPID_MOVE
"G0 [X] [Y] [Z] [T] [F] [S] ;[TOOLPATH_NAME] - Rapid"

+---------------------------------------------------

+ Commands output for the First Plunge Move, in a series of plunge moves.

+---------------------------------------------------

begin FIRST_PLUNGE_MOVE

"G1 [X] [Y] [Z] [FP] ;[TOOLPATH_NAME] - PLUNGE"


+---------------------------------------------------
+  Commands output for plunge moves
+---------------------------------------------------

begin PLUNGE_MOVE

"G1 [X] [Y] [Z] [FP]"


+---------------------------------------------------
+  Commands output for the first feed rate move
+---------------------------------------------------

begin FIRST_FEED_MOVE

"G1 [X] [Y] [Z] [FC] ;[TOOLPATH_NAME] - FEED"


+---------------------------------------------------
+  Commands output for feed rate moves
+---------------------------------------------------

begin FEED_MOVE

"G1 [X] [Y] [Z] [FC]"


+---------------------------------------------------
+  Commands output for the first clockwise arc move
+---------------------------------------------------

begin FIRST_CW_ARC_MOVE

"G2 [X] [Y] [Z] [IA] [JA] [FC] ;[TOOLPATH_NAME] - CW ARC"


+---------------------------------------------------
+  Commands output for clockwise arc  move
+---------------------------------------------------

begin CW_ARC_MOVE

"G2 [X] [Y] [Z] [IA] [JA]"


+---------------------------------------------------
+  Commands output for the first counterclockwise arc move
+---------------------------------------------------

begin FIRST_CCW_ARC_MOVE

"G3 [X] [Y] [Z] [IA] [JA] [FC] ;[TOOLPATH_NAME] - CCW ARC"


+---------------------------------------------------
+  Commands output for counterclockwise arc  move
+---------------------------------------------------

begin CCW_ARC_MOVE

"G3 [X] [Y] [Z] [IA] [JA]"


+---------------------------------------------------

+ Commands output at the end of the file

+---------------------------------------------------

begin FOOTER

".TRL"
"PARK"
".EOF"