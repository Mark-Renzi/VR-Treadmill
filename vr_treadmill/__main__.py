import time
from pynput.keyboard import Key, Listener
from pynput.mouse import Controller
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit, QLabel
import vgamepad as vg

gamepad = vg.VX360Gamepad()
mouse = Controller()
enabled = True
keyToggle = False

# -------------------------------------------------------------------
sensitivity = 400 # How sensitive the joystick will be
pollRate = 60 # How many times per second the mouse will be checked
quitKey = Key.ctrl_r # Which key will stop the program
# -------------------------------------------------------------------

class MainWindow(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Maratron")
        
        startJoy = QPushButton("Start")
        startJoy.clicked.connect(self.run)
        
        self.setKeyButton = QPushButton("Set Stop Key")
        self.setKeyButton.clicked.connect(self.setKey)
        
        pollLabel = QLabel("Polling Rate (/sec):")
        
        senseLabel = QLabel("Sensitivity:")
        
        self.keyLabel = QLabel("Stop Key: " + str(quitKey))
        
        pollRateLine = QLineEdit(str(pollRate))
        pollRateLine.textChanged.connect(self.setPollingRate)
        
        senseLine = QLineEdit(str(sensitivity))
        senseLine.textChanged.connect(self.setSensitivity)
        
        layout = QVBoxLayout()
        
        layout.addWidget(startJoy)
        layout.addWidget(senseLabel)
        layout.addWidget(senseLine)
        layout.addWidget(pollLabel)
        layout.addWidget(pollRateLine)
        layout.addWidget(self.keyLabel)
        layout.addWidget(self.setKeyButton)
        
        self.setLayout(layout)
        self.show()
        
    def setPollingRate(a, b):
        global pollRate
        if b != "":
            pollRate = int(b)
            print("Poll rate:", b)
    
    def setSensitivity(a, b):
        global sensitivity
        if b != "":
            sensitivity = int(b)
            print("Sensitivity:", b)
            
    def setKey(a, b):
        global quitKey
        global keyToggle
        if not keyToggle:
            a.keyLabel.setText("PRESS ANY KEY")
            a.setKeyButton.setText("Confirm?")
            print("Listening...")
            keyToggle = True
        else:
            a.keyLabel.setText("Stop Key: " + str(quitKey))
            a.setKeyButton.setText("Set Stop Key")
            print("Confirmed")
            keyToggle = False
        
        
    def run(a, b):
        global enabled
        global keyToggle
        enabled = True
        mousey = 0
        mousey1 = 0
        mousey2 = 0
        while enabled and not keyToggle:
            mousey2 = mousey1
            mousey1 = 0
            
            mousey1 = (mouse.position[1] - 500) * -(sensitivity) # convert mouse position to joystick value
            
            mousey = max(-32768, min(32767, int((mousey1 + mousey2)/2))) # average and clamp
            mouse.position = (700, 500) # reset mouse position, CHANGE THIS IF THE MOUSE IS OFF SCREEN
            print("Joystick y:", mousey)
            
            gamepad.left_joystick(x_value=0, y_value=mousey)  # values between -32768 and 32767
            
            gamepad.update()
            
            time.sleep(1 / pollRate)
        
def onPress(key):
    global enabled
    global keyToggle
    global quitKey
    if keyToggle:
        print("Stop key will be", str(key))
        quitKey = key
    elif key == quitKey:
        enabled = False
        print("Stopped with", quitKey)
        
listener = Listener(onPress)
listener.start()
        
app = QApplication([])
window = MainWindow()
window.show()
app.exec()

