import ctypes
import ctypes.wintypes as wintypes
from PyQt6 import QtCore

# Alias for brevity
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ---------------------------
# Constants
# ---------------------------
RIM_TYPEMOUSE = 0x00
RID_INPUT = 0x10000003
WM_INPUT = 0x00FF
RIDEV_INPUTSINK = 0x00000100

# Manually define missing wintypes
HCURSOR = wintypes.HANDLE
HICON = wintypes.HANDLE
HBRUSH = wintypes.HANDLE


# ---------------------------
# Raw input structures (same as provided snippet)
# ---------------------------
class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class _BUTTONS_STRUCT(ctypes.Structure):
    _fields_ = [
        ("usButtonFlags", wintypes.USHORT),
        ("usButtonData", wintypes.USHORT),
    ]


class _BUTTONS_UNION(ctypes.Union):
    _fields_ = [
        ("ulButtons", wintypes.ULONG),
        ("buttonsStruct", _BUTTONS_STRUCT),
    ]


class RAWMOUSE(ctypes.Structure):
    _anonymous_ = ("buttons",)
    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("buttons", _BUTTONS_UNION),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", ctypes.c_long),
        ("lLastY", ctypes.c_long),
        ("ulExtraInformation", wintypes.ULONG),
    ]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class RAWHID(ctypes.Structure):
    _fields_ = [
        ("dwSizeHid", wintypes.DWORD),
        ("dwCount", wintypes.DWORD),
        ("bRawData", ctypes.c_ubyte * 1),
    ]


class RAWINPUTUNION(ctypes.Union):
    _fields_ = [
        ("mouse", RAWMOUSE),
        ("keyboard", RAWKEYBOARD),
        ("hid", RAWHID),
    ]


class RAWINPUT(ctypes.Structure):
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", RAWINPUTUNION),
    ]


# ---------------------------
# WNDCLASS definition
# ---------------------------
WNDPROCTYPE = ctypes.WINFUNCTYPE(
    ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROCTYPE),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


# ---------------------------
# RawMouseListener Class
# ---------------------------
class RawMouseListener(QtCore.QThread):
    # Signal to emit mouse deltas (dx, dy)
    delta_signal = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.hwnd = None
        self.wnd_proc_ref = None  # Prevent GC of callback

    def create_message_window(self):
        hInstance = kernel32.GetModuleHandleW(None)
        className = "RawInputCaptureWindow"

        # The wnd_proc must be defined here to capture 'self' if needed,
        # but in this case, it just calls a method.
        @WNDPROCTYPE
        def wnd_proc(hwnd, msg, wParam, lParam):
            if msg == WM_INPUT:
                self.handle_raw_input(lParam)
            return user32.DefWindowProcW(
                wintypes.HWND(hwnd),
                wintypes.UINT(msg),
                wintypes.WPARAM(wParam),
                wintypes.LPARAM(lParam),
            )

        self.wnd_proc_ref = wnd_proc

        wc = WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc_ref
        wc.lpszClassName = className
        wc.hInstance = hInstance

        if not user32.RegisterClassW(ctypes.byref(wc)):
            raise ctypes.WinError()

        self.hwnd = user32.CreateWindowExW(
            0,
            className,
            "Hidden Raw Input Window",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            hInstance,
            None,
        )

        if not self.hwnd:
            raise ctypes.WinError()

    def register_raw_input(self):
        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01  # Generic Desktop Controls
        rid.usUsage = 0x02  # Mouse
        rid.dwFlags = RIDEV_INPUTSINK  # Listen even if not foreground
        rid.hwndTarget = self.hwnd

        if not user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(rid)):
            raise ctypes.WinError()

    def handle_raw_input(self, lParam):
        data_size = wintypes.UINT()

        if (
            user32.GetRawInputData(
                lParam,
                RID_INPUT,
                None,
                ctypes.byref(data_size),
                ctypes.sizeof(RAWINPUTHEADER),
            )
            != 0
        ):
            return  # Error or nothing to read

        buffer = ctypes.create_string_buffer(data_size.value)

        if (
            user32.GetRawInputData(
                lParam,
                RID_INPUT,
                buffer,
                ctypes.byref(data_size),
                ctypes.sizeof(RAWINPUTHEADER),
            )
            == data_size.value
        ):
            raw = RAWINPUT.from_buffer_copy(buffer.raw)
            if raw.header.dwType == RIM_TYPEMOUSE:
                dx = raw.data.mouse.lLastX
                dy = raw.data.mouse.lLastY
                self.delta_signal.emit(dx, dy)

    def run(self):
        try:
            self.create_message_window()
            self.register_raw_input()
            self.running = True
            print("Raw Mouse Listener started.")

            # Message loop - runs until PostQuitMessage or stop() is called.
            msg = wintypes.MSG()
            while (
                self.running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0
            ):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        except Exception as e:
            print(f"Raw Mouse Listener error: {e}")
        finally:
            self.running = False
            self.cleanup_window()
            print("Raw Mouse Listener stopped.")

    def stop(self):
        self.running = False
        if self.hwnd:
            # Post a quit message to break the message loop in the thread
            user32.PostQuitMessage(0)

    def cleanup_window(self):
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None
