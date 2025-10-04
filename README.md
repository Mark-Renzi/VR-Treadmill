# VR-Treadmill
script that converts mouse movement into joystick movement for a VR treadmill.
(requires Python3)


to bind the virtual gamepad using steam input, open the script in a text editor and comment out the indicated line. when the bind is set up, uncomment the line and restart the script.


REQUIRED: 

pip install pynput

pip install vgamepad

pip install PyQt6

To permanently change settings, edit treadmill.py and change the vaules between the dashes near the top.

FUTURE IDEAS:

using an openxr library to directly control the game instead of a virtual xbox360 controller
