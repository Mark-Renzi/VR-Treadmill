import ctypes
import ctypes.wintypes as wintypes
import sys

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Manually define missing wintypes
HCURSOR = wintypes.HANDLE
HICON = wintypes.HANDLE
HBRUSH = wintypes.HANDLE

RIM_TYPEMOUSE = 0x00
RID_INPUT = 0x10000003
WM_INPUT = 0x00FF
RIDEV_INPUTSINK = 0x00000100

MOUSE_MOVE_RELATIVE = 0
MOUSE_MOVE_ABSOLUTE = 1

# ---------------------------
# Raw input structures
# ---------------------------
class RAWINPUTDEVICE(ctypes.Structure):
#    _pack_ = 1
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]

class RAWINPUTHEADER(ctypes.Structure):
#    _pack_ = 1
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]

# Inner struct for button flags (union member)
class _BUTTONS_STRUCT(ctypes.Structure):
#    _pack_ = 1
    _fields_ = [
        ("usButtonFlags", wintypes.USHORT),
        ("usButtonData", wintypes.USHORT),
    ]

# Union of ulButtons and buttonStruct
class _BUTTONS_UNION(ctypes.Union):
#    _pack_ = 1
    _fields_ = [
        ("ulButtons", wintypes.ULONG),
        ("buttonsStruct", _BUTTONS_STRUCT),
    ]

class RAWMOUSE(ctypes.Structure):
#    _pack_ = 1
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
#    _pack_ = 1
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]

class RAWHID(ctypes.Structure):
#    _pack_ = 1
    _fields_ = [
        ("dwSizeHid", wintypes.DWORD),
        ("dwCount", wintypes.DWORD),
        ("bRawData", ctypes.c_ubyte * 1),
    ]

class RAWINPUTUNION(ctypes.Union):
#    _pack_ = 1
    _fields_ = [
        ("mouse", RAWMOUSE),
        ("keyboard", RAWKEYBOARD),
        ("hid", RAWHID),
    ]

class RAWINPUT(ctypes.Structure):
#    _pack_ = 1
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", RAWINPUTUNION),
    ]

# ---------------------------
# WNDCLASS definition
# ---------------------------
WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

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

# Store a global reference to avoid garbage collection
wnd_proc_ref = None

# ---------------------------
# Raw input handling
# ---------------------------
def handle_raw_input(lParam):
    data_size = wintypes.UINT()
    if user32.GetRawInputData(
        lParam,
        RID_INPUT,
        None,
        ctypes.byref(data_size),
        ctypes.sizeof(RAWINPUTHEADER)
    ) != 0:
        raise ctypes.WinError()
    else:
        buffer = ctypes.create_string_buffer(data_size.value)

    if user32.GetRawInputData(
        lParam,
        RID_INPUT,
        buffer,
        ctypes.byref(data_size),
        ctypes.sizeof(RAWINPUTHEADER),
    ) != data_size.value:
        raise ctypes.WinError()
    
    # print("Expected struct size:", ctypes.sizeof(RAWINPUT))
    # print("Buffer size returned:", data_size.value)

    raw = RAWINPUT.from_buffer_copy(buffer.raw)
    if raw.header.dwType == RIM_TYPEMOUSE:
        flags = raw.data.mouse.usFlags
        dx = raw.data.mouse.lLastX
        dy = raw.data.mouse.lLastY

        print(f"Flags: {flags}, dx: {dx}, dy: {dy}")

# ---------------------------
# Create message window
# ---------------------------
def create_message_window():
    global wnd_proc_ref

    hInstance = kernel32.GetModuleHandleW(None)
    className = "RawInputCaptureWindow"

    @WNDPROCTYPE
    def wnd_proc(hwnd, msg, wParam, lParam):
        if msg == WM_INPUT:
            handle_raw_input(lParam)
        return user32.DefWindowProcW(
            wintypes.HWND(hwnd),
            wintypes.UINT(msg),
            wintypes.WPARAM(wParam),
            wintypes.LPARAM(lParam)
        )


    wnd_proc_ref = wnd_proc  # prevent GC

    wc = WNDCLASS()
    wc.lpfnWndProc = wnd_proc_ref
    wc.lpszClassName = className
    wc.hInstance = hInstance
    wc.hbrBackground = HBRUSH(0)
    wc.hCursor = HCURSOR(0)
    wc.hIcon = HICON(0)
    wc.style = 0
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.lpszMenuName = None

    if not user32.RegisterClassW(ctypes.byref(wc)):
        raise ctypes.WinError()

    hwnd = user32.CreateWindowExW(
        0,
        className,
        "Hidden Raw Input Window",
        0,
        0, 0, 0, 0,
        None, None, hInstance, None,
    )

    if not hwnd:
        raise ctypes.WinError()

    return hwnd

def register_raw_input(hwnd):
    rid = RAWINPUTDEVICE()
    rid.usUsagePage = 0x01
    rid.usUsage = 0x02
    rid.dwFlags = RIDEV_INPUTSINK
    rid.hwndTarget = hwnd

    if not user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(rid)):
        raise ctypes.WinError()

def message_loop():
    msg = wintypes.MSG()
    while True:
        bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if bRet == 0:
            break
        elif bRet == -1:
            raise ctypes.WinError()
        else:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    hwnd = create_message_window()
    register_raw_input(hwnd)
    print("Listening for raw mouse input...")
    try:
        message_loop()
    except KeyboardInterrupt:
        print("Exiting.")
        sys.exit(0)
