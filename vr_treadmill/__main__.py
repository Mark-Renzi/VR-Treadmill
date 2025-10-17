import time
from pynput.keyboard import Key, Listener
from pynput.mouse import Controller
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
    QLabel,
)
import vgamepad as vg

gamepad = vg.VX360Gamepad()
mouse = Controller()
enabled = True
keyToggle = False

# -------------------------------------------------------------------
sensitivity = 400  # How sensitive the joystick will be
pollRate = 60  # How many times per second the mouse will be checked
quitKey = Key.ctrl_r  # Which key will stop the program
# -------------------------------------------------------------------


class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Maratron")

        self.startJoy = QPushButton("Start")
        self.startJoy.clicked.connect(self.run)

        self.setKeyButton = QPushButton("Set Stop Key")
        self.setKeyButton.clicked.connect(self.setKey)

        pollLabel = QLabel("Polling Rate (/sec):")
        senseLabel = QLabel("Sensitivity:")

        self.keyLabel = QLabel("Stop Key: " + str(quitKey))

        self.pollRateLine = QLineEdit(str(pollRate))
        self.pollRateLine.textChanged.connect(self.setPollingRate)

        self.senseLine = QLineEdit(str(sensitivity))
        self.senseLine.textChanged.connect(self.setSensitivity)

        layout = QVBoxLayout()
        layout.addWidget(self.startJoy)
        layout.addWidget(senseLabel)
        layout.addWidget(self.senseLine)
        layout.addWidget(pollLabel)
        layout.addWidget(self.pollRateLine)
        layout.addWidget(self.keyLabel)
        layout.addWidget(self.setKeyButton)

        self.setLayout(layout)
        self.show()

        # Input validation tracking
        self.validSensitivity = True
        self.validPollRate = True

    def updateStartButton(self):
        self.startJoy.setEnabled(self.validSensitivity and self.validPollRate)

    def setPollingRate(self, value):
        global pollRate
        try:
            val = int(value)
            if val <= 0:
                raise ValueError
            pollRate = val
            self.validPollRate = True
            print("Poll rate:", val)
        except ValueError:
            self.validPollRate = False
            print("Invalid polling rate")
        self.updateStartButton()

    def setSensitivity(self, value):
        global sensitivity
        try:
            val = int(value)
            if val <= 0:
                raise ValueError
            sensitivity = val
            self.validSensitivity = True
            print("Sensitivity:", val)
        except ValueError:
            self.validSensitivity = False
            print("Invalid sensitivity")
        self.updateStartButton()

    def setKey(self):
        global quitKey
        global keyToggle
        if not keyToggle:
            self.keyLabel.setText("PRESS ANY KEY")
            self.setKeyButton.setText("Confirm?")
            print("Listening...")
            keyToggle = True
        else:
            self.keyLabel.setText("Stop Key: " + str(quitKey))
            self.setKeyButton.setText("Set Stop Key")
            print("Confirmed")
            keyToggle = False

    def run(self):
        global enabled
        global keyToggle
        enabled = True
        mousey = 0
        mousey1 = 0
        mousey2 = 0

        while enabled and not keyToggle:
            mousey2 = mousey1
            mousey1 = 0

            mousey1 = (mouse.position[1] - 500) * -(
                sensitivity
            )  # convert mouse position to joystick value

            mousey = max(
                -32768, min(32767, int((mousey1 + mousey2) / 2))
            )  # average and clamp
            mouse.position = (700, 500)  # reset mouse position
            print("Joystick y:", mousey)

            gamepad.left_joystick(
                x_value=0, y_value=mousey
            )  # values between -32768 and 32767
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


listener = Listener(on_press=onPress)
listener.start()

app = QApplication([])
window = MainWindow()
window.show()
app.exec()
