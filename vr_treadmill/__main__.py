import signal
import sys
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
    QCheckBox,
)
import vgamepad as vg
from vr_treadmill.curve_editor import CurveEditorWindow
from vr_treadmill.raw_mouse_listener import RawMouseListener 

gamepad = vg.VX360Gamepad()
mouse = Controller()
enabled = False

useRawInput = False
mouseDeltaY = 0

keyToggle = False

aKey = Key.alt_gr
aKeyToggle = False

recenterEnabled = True
recenterToggleKey = Key.f9
recenterKeyToggle = False

# -------------------------------------------------------------------
sensitivity = 400  # How sensitive the joystick will be
pollRate = 60  # How many times per second the mouse will be checked
quitKey = Key.ctrl_r  # Which key will stop the program
# -------------------------------------------------------------------


class JoystickWorker(QtCore.QThread):
    update_input = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False

    def start_loop(self):
        self.running = True
        self.start()

    def stop_loop(self):
        self.running = False

    def run(self):
        global sensitivity, pollRate, window, recenterEnabled, useRawInput, mouseDeltaY

        while enabled and not keyToggle:
            cycle_start = time.perf_counter()
            current_sensitivity = sensitivity
            
            if useRawInput:
                # Use the accumulated delta from the raw input listener
                # Reset the delta for the next cycle
                delta_y = mouseDeltaY
                mouseDeltaY = 0 
            else:
                # Traditional polling and recentering logic
                delta_y = mouse.position[1] - 500
                if recenterEnabled:
                    mouse.position = (700, 500)
            
            scaled_input = abs(delta_y) * current_sensitivity

            # Emit signal to update the curve editor with current input
            self.update_input.emit(min(int(scaled_input), 32767))

            use_curve = (
                hasattr(window, "curveWindow") and window.curveWindow.isVisible()
            )
            show_dot = window.showDotCheckbox.isChecked()

            if use_curve:
                curve_lut = window.curveWindow.get_or_build_curve_mapping()
                output_magnitude = window.interpolate_curve(scaled_input, curve_lut)

                if show_dot:
                    window.curveWindow.set_current_input(int(min(scaled_input, 32767)))
            else:
                output_magnitude = scaled_input

            if delta_y > 0:
                mousey = -int(output_magnitude)
            elif delta_y < 0:
                mousey = int(output_magnitude)
            else:
                mousey = 0

            clamped_mousey = max(-32768, min(32767, mousey))
            
            print("Joystick y:", clamped_mousey)

            gamepad.left_joystick(x_value=0, y_value=clamped_mousey)
            gamepad.update()

            elapsed = time.perf_counter() - cycle_start
            
            sleep_time = max(0, (1 / pollRate) - elapsed)
            time.sleep(sleep_time)


class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.worker = JoystickWorker()
        self.worker.update_input.connect(self.update_curve_input)
        
        self.raw_listener = RawMouseListener()
        self.raw_listener.delta_signal.connect(self.update_mouse_delta)

        self.setWindowTitle("Maratron")

        self.startStopButton = QPushButton("Start")
        self.startStopButton.clicked.connect(self.toggleTracking)

        self.setKeyButton = QPushButton("Set Stop Key")
        self.setKeyButton.clicked.connect(self.setKey)

        self.setAKeyButton = QPushButton("Set A Button Key")
        self.setAKeyButton.clicked.connect(self.setAKey)

        self.aKeyLabel = QLabel(f"A Button Key: {aKey}")

        self.setRecenterKeyButton = QPushButton("Set Recenter Toggle Key")
        self.setRecenterKeyButton.clicked.connect(self.setRecenterKey)

        self.recenterKeyLabel = QLabel(f"Recenter Toggle Key: {recenterToggleKey}")

        pollLabel = QLabel("Polling Rate (/sec):")
        senseLabel = QLabel("Sensitivity:")

        self.keyLabel = QLabel(f"Stop Key: {quitKey}")

        self.pollRateLine = QLineEdit(str(pollRate))
        self.pollRateLine.textChanged.connect(self.setPollingRate)

        self.senseLine = QLineEdit(str(sensitivity))
        self.senseLine.textChanged.connect(self.setSensitivity)

        self.openCurveEditorButton = QPushButton("Edit Sensitivity Curve")
        self.openCurveEditorButton.clicked.connect(self.openCurveEditor)

        self.showDotCheckbox = QCheckBox("Show Input on Curve")
        
        self.rawInputCheckbox = QCheckBox("Use Raw Input (Disables Recenter)")
        self.rawInputCheckbox.stateChanged.connect(self.toggleRawInput)


        layout = QVBoxLayout()
        layout.addWidget(self.startStopButton)
        layout.addWidget(senseLabel)
        layout.addWidget(self.senseLine)
        layout.addWidget(pollLabel)
        layout.addWidget(self.pollRateLine)
        layout.addWidget(self.keyLabel)
        layout.addWidget(self.setKeyButton)
        layout.addWidget(self.aKeyLabel)
        layout.addWidget(self.setAKeyButton)
        layout.addWidget(self.recenterKeyLabel)
        layout.addWidget(self.setRecenterKeyButton)
        layout.addWidget(self.rawInputCheckbox)
        layout.addWidget(self.openCurveEditorButton)
        layout.addWidget(self.showDotCheckbox)

        self.setLayout(layout)
        self.show()

        # Input validation tracking
        self.validSensitivity = True
        self.validPollRate = True

    def toggleRawInput(self, state):
        global useRawInput, recenterEnabled
        useRawInput = (state == 2)
        
        # Disable recentering when raw input is on
        if useRawInput:
            recenterEnabled = False
            self.recenterKeyLabel.setText("Recenter disabled (Raw Input ON)")
            self.setRecenterKeyButton.setEnabled(False)
            print("Raw Input ON. Mouse recentering OFF.")
        else:
            self.setRecenterKeyButton.setEnabled(True)
            self.recenterKeyLabel.setText(f"Recenter Toggle Key: {recenterToggleKey}")
            print("Raw Input OFF.")

    @QtCore.pyqtSlot(int, int)
    def update_mouse_delta(self, dx, dy):
        """Accumulate mouse deltas from the RawMouseListener thread."""
        global mouseDeltaY
        mouseDeltaY += dy


    def update_curve_input(self, input_value: int):
        if (
            hasattr(self, "curveWindow")
            and self.curveWindow.isVisible()
            and self.showDotCheckbox.isChecked()
        ):
            self.curveWindow.set_current_input(input_value)

    def updateStartButton(self):
        self.startStopButton.setEnabled(self.validSensitivity and self.validPollRate)

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

    def updateStartStopButtonText(self):
        """Updates the text of the Start/Stop button based on the global 'enabled' state."""
        self.startStopButton.setText("Stop" if enabled else "Start")

    def toggleTracking(self):
            """Handles starting and stopping the tracking when the button is pressed."""
            global enabled, keyToggle, useRawInput, mouseDeltaY

            if enabled:
                enabled = False
                self.worker.stop_loop()
                
                mouseDeltaY = 0

                print("Tracking stopped via GUI button.")
            else:
                enabled = True
                if useRawInput and not self.raw_listener.isRunning():
                    self.raw_listener.start()
                
                if not self.worker.isRunning():
                    self.worker.start_loop()
                    print("Tracking started.")
                else:
                    print("Worker is already running or being started.")
                
            self.updateStartStopButtonText()

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

    def setRecenterKey(self):
        global recenterToggleKey, recenterKeyToggle
        if not recenterKeyToggle:
            self.recenterKeyLabel.setText("PRESS ANY KEY")
            self.setRecenterKeyButton.setText("Confirm?")
            print("Listening for recenter toggle key...")
            recenterKeyToggle = True
        else:
            self.recenterKeyLabel.setText(f"Recenter Toggle Key: {recenterToggleKey}")
            self.setRecenterKeyButton.setText("Set Recenter Toggle Key")
            print("Recenter toggle key confirmed.")
            recenterKeyToggle = False


def onPress(key):
    global \
        enabled, \
        keyToggle, \
        quitKey, \
        aKeyToggle, \
        aKey, \
        recenterToggleKey, \
        recenterEnabled, \
        useRawInput
        
    if keyToggle:
        print("Stop key will be", str(key))
        quitKey = key
    elif aKeyToggle:
        print("A key will be", str(key))
        aKey = key
    elif enabled:
        if key == quitKey:
            global mouseDeltaY
            enabled = False
            window.worker.stop_loop()
            
            mouseDeltaY = 0

            if hasattr(window, "curveWindow") and window.curveWindow.isVisible():
                window.curveWindow.clear_current_input()
            
            window.updateStartStopButtonText() 

            print("Stopped with", quitKey)
        elif key == aKey:
            print("A key held:", key)
            gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            gamepad.update()
        elif recenterKeyToggle:
            print("Recenter toggle key will be", str(key))
            recenterToggleKey = key
        # Only allow recenter toggle if raw input is NOT enabled
        elif key == recenterToggleKey and not useRawInput:
            recenterEnabled = not recenterEnabled
            print(f"Mouse recentering {'enabled' if recenterEnabled else 'disabled'}")


def onRelease(key):
    global enabled
    global aKey

    if enabled and key == aKey:
        print("A key released:", key)
        gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        gamepad.update()


def cleanup():
    global window, listener
    print("Cleaning up...")

    if hasattr(window, "worker") and window.worker.isRunning():
        window.worker.stop_loop()
        window.worker.wait()
    
    if hasattr(window, "raw_listener") and window.raw_listener.isRunning():
        window.raw_listener.stop()
        window.raw_listener.wait()

    if listener.running:
        listener.stop()

    if hasattr(window, "curveWindow") and window.curveWindow.isVisible():
        window.curveWindow.clear_current_input()

    print("Exited cleanly.")
    app.quit()
    sys.exit(0)


# Handle SIGINT (Ctrl+C) properly
signal.signal(signal.SIGINT, lambda sig, frame: cleanup())


listener = Listener(on_press=onPress, on_release=onRelease)
listener.start()

try:
    app = QApplication([])
    window = MainWindow()
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    app.exec()
except KeyboardInterrupt:
    cleanup()
