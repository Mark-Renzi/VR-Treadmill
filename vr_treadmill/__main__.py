import os
import json
import signal
import sys
import time
from pynput.keyboard import Key, Listener
from pynput.mouse import Controller
from PyQt6 import QtCore
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
    QLabel,
    QCheckBox,
    QRadioButton,
    QGroupBox,
    QHBoxLayout,
    QComboBox,
    QInputDialog,
)
from threading import Lock
import vgamepad as vg
from vr_treadmill.curve_editor import CurveEditorWindow
from vr_treadmill.raw_mouse_listener import RawMouseListener
import statistics

gamepad = vg.VX360Gamepad()
mouse = Controller()
enabled = False

useRawInput = True
mouseDeltaY = 0
mouseDeltaLock = Lock()

keyToggle = False

aKey = Key.alt_gr
aKeyToggle = False

recenterEnabled = False
recenterToggleKey = Key.f9
recenterKeyToggle = False

# -------------------------------------------------------------------
sensitivity = 100  # How sensitive the joystick will be
pollRate = 60  # How many times per second the mouse will be checked
quitKey = Key.ctrl_r  # Which key will stop the program
averageCount = 5  # Number of data points in the smoothing window.
# -------------------------------------------------------------------

SMOOTHING_TYPE_MEAN = 0
SMOOTHING_TYPE_MEDIAN = 1
SMOOTHING_TYPE_MAX = 2
smoothingType = SMOOTHING_TYPE_MEAN

CONFIG_DIR = "./configs"
os.makedirs(CONFIG_DIR, exist_ok=True)


class JoystickWorker(QtCore.QThread):
    update_input = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.mouseDeltaHistory = []

    def start_loop(self):
        self.running = True
        self.start()

    def stop_loop(self):
        self.running = False
        self.mouseDeltaHistory = []

    def run(self):
        global \
            sensitivity, \
            pollRate, \
            window, \
            recenterEnabled, \
            useRawInput, \
            mouseDeltaY, \
            averageCount, \
            smoothingType, \
            mouseDeltaLock

        next_time = time.perf_counter()

        while enabled and not keyToggle:
            now = time.perf_counter()

            if now >= next_time:
                current_sensitivity = sensitivity

                if useRawInput:
                    with mouseDeltaLock:
                        delta_y_current = mouseDeltaY
                        mouseDeltaY = 0
                else:
                    delta_y_current = mouse.position[1] - 500
                    if recenterEnabled:
                        mouse.position = (700, 500)

                self.mouseDeltaHistory.append(delta_y_current)

                if len(self.mouseDeltaHistory) > averageCount:
                    self.mouseDeltaHistory = self.mouseDeltaHistory[-averageCount:]

                if self.mouseDeltaHistory:
                    if smoothingType == SMOOTHING_TYPE_MEAN:
                        delta_y = statistics.mean(self.mouseDeltaHistory)
                    elif smoothingType == SMOOTHING_TYPE_MEDIAN:
                        delta_y = statistics.median(self.mouseDeltaHistory)
                    elif smoothingType == SMOOTHING_TYPE_MAX:
                        delta_y = max(self.mouseDeltaHistory, key=abs)
                    else:
                        delta_y = statistics.mean(self.mouseDeltaHistory)
                else:
                    delta_y = 0

                scaled_input = abs(delta_y) * current_sensitivity

                use_curve = (
                    hasattr(window, "curveWindow") and window.curveWindow.isVisible()
                )

                if use_curve:
                    curve_lut = window.curveWindow.get_or_build_curve_mapping()
                    output_magnitude = window.interpolate_curve(scaled_input, curve_lut)

                    if window.showDotCheckbox.isChecked():
                        self.update_input.emit(
                            min(int(abs(delta_y) * current_sensitivity), 32767)
                        )
                else:
                    output_magnitude = scaled_input

                mousey = (
                    -int(output_magnitude)
                    if delta_y > 0
                    else int(output_magnitude)
                    if delta_y < 0
                    else 0
                )
                clamped_mousey = max(-32768, min(32767, mousey))

                print("Joystick y:", clamped_mousey)

                gamepad.left_joystick(x_value=0, y_value=clamped_mousey)
                gamepad.update()

                # Schedule next run
                next_time += 1.0 / pollRate

                # Catch up if behind
                if now > next_time:
                    next_time = now
            else:
                time.sleep(0.001)  # Yield CPU


class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.worker = JoystickWorker()
        self.worker.update_input.connect(self.update_curve_input)

        self.raw_listener = RawMouseListener()
        self.raw_listener.delta_signal.connect(self.update_mouse_delta)

        self.setWindowTitle("Maratron")
        self.setWindowIcon(QIcon("./resources/mini.ico"))

        self.startStopButton = QPushButton("Start")
        self.startStopButton.clicked.connect(self.toggleTracking)

        self.setKeyButton = QPushButton("Set Stop Key")
        self.setKeyButton.clicked.connect(self.setKey)

        self.setAKeyButton = QPushButton("Set A Button Key")
        self.setAKeyButton.clicked.connect(self.setAKey)

        self.aKeyLabel = QLabel(f"A Button Key: {aKey}")

        self.setRecenterKeyButton = QPushButton("Set Recenter Toggle Key")
        self.setRecenterKeyButton.clicked.connect(self.setRecenterKey)

        self.recenterKeyLabel = QLabel(f"Recenter disabled (Raw Input ON)")

        pollLabel = QLabel("Polling Rate (/sec):")
        senseLabel = QLabel("Sensitivity:")
        avgLabel = QLabel("Data Points in Smoothing Window (1 = Off):")
        self.keyLabel = QLabel(f"Stop Key: {quitKey}")

        self.pollRateLine = QLineEdit(str(pollRate))
        self.pollRateLine.textChanged.connect(self.setPollingRate)

        self.senseLine = QLineEdit(str(sensitivity))
        self.senseLine.textChanged.connect(self.setSensitivity)

        self.avgLine = QLineEdit(str(averageCount))
        self.avgLine.textChanged.connect(self.setAverageCount)

        self.openCurveEditorButton = QPushButton("Edit Sensitivity Curve")
        self.openCurveEditorButton.clicked.connect(self.openCurveEditor)

        self.showDotCheckbox = QCheckBox("Show Input on Curve")

        self.rawInputCheckbox = QCheckBox("Use Raw Input (Windows)")
        self.rawInputCheckbox.stateChanged.connect(self.toggleRawInput)
        self.rawInputCheckbox.setChecked(useRawInput)

        self.setRecenterKeyButton.setEnabled(not useRawInput)

        self.smoothingGroup = QGroupBox("Smoothing Type")
        self.meanRadio = QRadioButton("Mean")
        self.medianRadio = QRadioButton("Median")
        self.maxRadio = QRadioButton("Peak")

        if smoothingType == SMOOTHING_TYPE_MEAN:
            self.meanRadio.setChecked(True)
        elif smoothingType == SMOOTHING_TYPE_MEDIAN:
            self.medianRadio.setChecked(True)
        elif smoothingType == SMOOTHING_TYPE_MAX:
            self.maxRadio.setChecked(True)

        self.meanRadio.toggled.connect(
            lambda: self.setSmoothingType(SMOOTHING_TYPE_MEAN)
        )
        self.medianRadio.toggled.connect(
            lambda: self.setSmoothingType(SMOOTHING_TYPE_MEDIAN)
        )
        self.maxRadio.toggled.connect(lambda: self.setSmoothingType(SMOOTHING_TYPE_MAX))

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.meanRadio)
        h_layout.addWidget(self.medianRadio)
        h_layout.addWidget(self.maxRadio)
        self.smoothingGroup.setLayout(h_layout)

        self.configDropdown = QComboBox()
        self.loadConfigButton = QPushButton("Load Config")
        self.saveConfigButton = QPushButton("Save Config")

        self.loadConfigButton.clicked.connect(self.load_config)
        self.saveConfigButton.clicked.connect(lambda: self.save_config())

        self.update_config_dropdown()

        layout = QVBoxLayout()
        layout.addWidget(self.startStopButton)
        layout.addWidget(senseLabel)
        layout.addWidget(self.senseLine)
        layout.addWidget(pollLabel)
        layout.addWidget(self.pollRateLine)
        layout.addWidget(avgLabel)
        layout.addWidget(self.avgLine)
        layout.addWidget(self.smoothingGroup)
        layout.addWidget(self.keyLabel)
        layout.addWidget(self.setKeyButton)
        layout.addWidget(self.aKeyLabel)
        layout.addWidget(self.setAKeyButton)
        layout.addWidget(self.recenterKeyLabel)
        layout.addWidget(self.setRecenterKeyButton)
        layout.addWidget(self.rawInputCheckbox)
        layout.addWidget(self.openCurveEditorButton)
        layout.addWidget(self.showDotCheckbox)
        layout.addWidget(QLabel("Config:"))
        layout.addWidget(self.configDropdown)
        layout.addWidget(self.loadConfigButton)
        layout.addWidget(self.saveConfigButton)

        self.setLayout(layout)
        self.show()

        # Input validation tracking
        self.validSensitivity = True
        self.validPollRate = True
        self.validAverageCount = True

    def toggleRawInput(self, state):
        global useRawInput, recenterEnabled
        useRawInput = state == 2

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
        with mouseDeltaLock:
            mouseDeltaY += dy

    def update_curve_input(self, input_value: int):
        if (
            hasattr(self, "curveWindow")
            and self.curveWindow.isVisible()
            and self.showDotCheckbox.isChecked()
        ):
            self.curveWindow.set_current_input(input_value)

    def updateStartButton(self):
        self.startStopButton.setEnabled(
            self.validSensitivity and self.validPollRate and self.validAverageCount
        )

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

    def setAverageCount(self, value):
        global averageCount
        try:
            val = int(value)
            if val <= 0:
                raise ValueError
            averageCount = val
            self.validAverageCount = True
            print("Averaging count:", val)
            if self.worker.isRunning():
                self.worker.mouseDeltaHistory = []
        except ValueError:
            self.validAverageCount = False
            print("Invalid averaging count (must be a positive integer)")
        self.updateStartButton()

    def setSmoothingType(self, type_id):
        """Sets the global smoothing type based on the radio button selection."""
        global smoothingType
        if type_id == SMOOTHING_TYPE_MEAN and self.meanRadio.isChecked():
            smoothingType = SMOOTHING_TYPE_MEAN
            print("Smoothing type set to: Mean")
        elif type_id == SMOOTHING_TYPE_MEDIAN and self.medianRadio.isChecked():
            smoothingType = SMOOTHING_TYPE_MEDIAN
            print("Smoothing type set to: Median")
        elif type_id == SMOOTHING_TYPE_MAX and self.maxRadio.isChecked():
            smoothingType = SMOOTHING_TYPE_MAX
            print("Smoothing type set to: Peak")

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
                self.save_config(name="latest_config")
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

    def get_current_config(self):
        return {
            "sensitivity": self.senseLine.text(),
            "poll_rate": self.pollRateLine.text(),
            "average_count": self.avgLine.text(),
            "smoothing_type": smoothingType,
            "raw_input": useRawInput,
            "stop_key": str(quitKey),
            "a_key": str(aKey),
            "recenter_key": str(recenterToggleKey),
            "recenter_enabled": recenterEnabled,
            "curve_editor_open": hasattr(self, "curveWindow")
            and self.curveWindow.isVisible(),
            "show_input_on_curve": self.showDotCheckbox.isChecked(),
            "curve_points": self.curveWindow.serialize_points()
            if hasattr(self, "curveWindow")
            else None,
        }

    def apply_config(self, config):
        global quitKey, aKey, recenterToggleKey, recenterEnabled

        self.senseLine.setText(str(config.get("sensitivity", "100")))
        self.pollRateLine.setText(str(config.get("poll_rate", "60")))
        self.avgLine.setText(str(config.get("average_count", "5")))

        smoothing = config.get("smoothing_type", SMOOTHING_TYPE_MEAN)
        if smoothing == SMOOTHING_TYPE_MEAN:
            self.meanRadio.setChecked(True)
        elif smoothing == SMOOTHING_TYPE_MEDIAN:
            self.medianRadio.setChecked(True)
        elif smoothing == SMOOTHING_TYPE_MAX:
            self.maxRadio.setChecked(True)

        self.rawInputCheckbox.setChecked(config.get("raw_input", True))

        # Restore key binds
        quitKey = self._key_from_string(config.get("stop_key", str(Key.ctrl_r)))
        aKey = self._key_from_string(config.get("a_key", str(Key.alt_gr)))
        recenterToggleKey = self._key_from_string(
            config.get("recenter_key", str(Key.f9))
        )
        recenterEnabled = config.get("recenter_enabled", False)

        self.keyLabel.setText(f"Stop Key: {quitKey}")
        self.aKeyLabel.setText(f"A Button Key: {aKey}")
        if not useRawInput:
            self.recenterKeyLabel.setText(f"Recenter Toggle Key: {recenterToggleKey}")

        if config.get("curve_editor_open", False):
            self.openCurveEditor()

            points_data = config.get("curve_points")
            if points_data and hasattr(self, "curveWindow"):
                self.curveWindow.deserialize_points(points_data)

        self.showDotCheckbox.setChecked(config.get("show_input_on_curve", False))

    def _key_from_string(self, key_str):
        try:
            if key_str.startswith("Key."):
                return getattr(Key, key_str[4:])
            else:
                return key_str
        except Exception as e:
            print(f"Failed to parse key from string '{key_str}': {e}")
            return Key.ctrl_r

    def save_config(self, name=None):
        if name is None:
            text, ok = QInputDialog.getText(self, "Save Config", "Enter config name:")
            if not ok or not text.strip():
                print("Save cancelled or name was empty.")
                return
            name = text.strip()

        config = self.get_current_config()
        path = os.path.join(CONFIG_DIR, f"{name}.json")
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=4)
            print(f"Config '{name}' saved.")
            self.update_config_dropdown()
        except Exception as e:
            print(f"Failed to save config: {e}")

    def load_config(self):
        name = self.configDropdown.currentText()
        if not name:
            return
        path = os.path.join(CONFIG_DIR, f"{name}.json")
        try:
            with open(path, "r") as f:
                config = json.load(f)
                self.apply_config(config)
                print(f"Config '{name}' loaded.")
        except Exception as e:
            print(f"Failed to load config '{name}': {e}")

    def update_config_dropdown(self):
        self.configDropdown.clear()
        configs = [f[:-5] for f in os.listdir(CONFIG_DIR) if f.endswith(".json")]
        self.configDropdown.addItems(sorted(configs))


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


# handle CTRL+C
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
