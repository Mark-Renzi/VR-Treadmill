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
from vr_treadmill.curve_editor import CurveEditorWindow

gamepad = vg.VX360Gamepad()
mouse = Controller()
enabled = False
keyToggle = False
aKey = Key.alt_gr
aKeyToggle = False

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

        self.setAKeyButton = QPushButton("Set A Key")
        self.setAKeyButton.clicked.connect(self.setAKey)

        self.aKeyLabel = QLabel(f"A Button Key: {aKey}")

        pollLabel = QLabel("Polling Rate (/sec):")
        senseLabel = QLabel("Sensitivity:")

        self.keyLabel = QLabel(f"Stop Key: {quitKey}")

        self.pollRateLine = QLineEdit(str(pollRate))
        self.pollRateLine.textChanged.connect(self.setPollingRate)

        self.senseLine = QLineEdit(str(sensitivity))
        self.senseLine.textChanged.connect(self.setSensitivity)

        self.openCurveEditorButton = QPushButton("Edit Sensitivity Curve")
        self.openCurveEditorButton.clicked.connect(self.openCurveEditor)

        layout = QVBoxLayout()
        layout.addWidget(self.startJoy)
        layout.addWidget(senseLabel)
        layout.addWidget(self.senseLine)
        layout.addWidget(pollLabel)
        layout.addWidget(self.pollRateLine)
        layout.addWidget(self.keyLabel)
        layout.addWidget(self.setKeyButton)
        layout.addWidget(self.aKeyLabel)
        layout.addWidget(self.setAKeyButton)
        layout.addWidget(self.openCurveEditorButton)

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

    def setAKey(self):
        global aKey
        global aKeyToggle
        if not aKeyToggle:
            self.aKeyLabel.setText("PRESS ANY KEY")
            self.setAKeyButton.setText("Confirm?")
            print("Listening for A key bind...")
            aKeyToggle = True
        else:
            if aKey:
                self.aKeyLabel.setText("A Button Key: " + str(aKey))
            else:
                self.aKeyLabel.setText("A Button Key: Not set")
            self.setAKeyButton.setText("Set A Key")
            print("A Key binding confirmed.")
            aKeyToggle = False

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
        mousey1 = 0
        mousey2 = 0

        while enabled and not keyToggle:
            cycle_start = time.perf_counter()
            current_sensitivity = sensitivity  # Read latest value
            mousey2 = mousey1
            mousey1 = 0

            delta_y = mouse.position[1] - 500
            scaled_input = abs(delta_y) * current_sensitivity

            use_curve = hasattr(self, "curveWindow") and self.curveWindow.isVisible()
            if use_curve:
                curve_lut = self.curveWindow.get_or_build_curve_mapping()
                output_magnitude = self.interpolate_curve(scaled_input, curve_lut)
            else:
                output_magnitude = scaled_input

            if delta_y > 0:
                mousey = -int(output_magnitude)
            elif delta_y < 0:
                mousey = int(output_magnitude)
            else:
                mousey = 0

            mousey_avg = max(-32768, min(32767, (mousey + mousey2) // 2))
            mouse.position = (700, 500)

            print("Joystick y:", mousey_avg)

            gamepad.left_joystick(x_value=0, y_value=mousey_avg)
            gamepad.update()

            elapsed = time.perf_counter() - cycle_start
            sleep_time = max(0, (1 / pollRate) - elapsed)
            time.sleep(sleep_time)

    def openCurveEditor(self):
        self.curveWindow = CurveEditorWindow()
        self.curveWindow.show()

    def interpolate_curve(self, input_value, curve):
        """Linearly interpolate output from the curve based on input."""
        for i in range(len(curve) - 1):
            x1, y1 = curve[i]
            x2, y2 = curve[i + 1]
            if x1 <= input_value <= x2:
                # Linear interpolation
                ratio = (input_value - x1) / (x2 - x1)
                return y1 + ratio * (y2 - y1)
        # If input is out of bounds, clamp to end values
        if input_value < curve[0][0]:
            return curve[0][1]
        else:
            return curve[-1][1]


def onPress(key):
    global enabled
    global keyToggle
    global quitKey
    global aKeyToggle
    global aKey

    if keyToggle:
        print("Stop key will be", str(key))
        quitKey = key
    elif aKeyToggle:
        print("A key will be", str(key))
        aKey = key
    elif enabled:
        if key == quitKey:
            enabled = False
            print("Stopped with", quitKey)
        elif key == aKey:
            print("A key held:", key)
            gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            gamepad.update()


def onRelease(key):
    global enabled
    global aKey

    if enabled and key == aKey:
        print("A key released:", key)
        gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        gamepad.update()


listener = Listener(on_press=onPress, on_release=onRelease)
listener.start()

app = QApplication([])
window = MainWindow()
window.show()
app.exec()
