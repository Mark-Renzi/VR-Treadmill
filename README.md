# VR-Treadmill
Script that converts mouse movement into joystick movement for a VR treadmill.

This version adds some more features, including:
- Raw mouse input to avoid locking the mouse or hitting the edge of the screen
- Various input smoothing methods
- Sensitivity remapping and visualization
- Config saving and loading

<img width="1160" height="1348" alt="image" src="https://github.com/user-attachments/assets/dc4ccab1-3090-49a1-88f1-acd06216b935" />


## Install Process

You can install with pip or uv. If you're going to develop, use uv, but it's not required.

### uv
I recommend [astral's uv](https://docs.astral.sh/uv/getting-started/installation/), a fast package manager that can be used as a compatible drop-in replacement for pip. It can take full advantage of the pyproject file for developers.

```shell
uv venv --python 3.13
uv pip install -e .
```

Activate this new environment:
```shell
# Windows
./venv/Scripts/activate

# MacOS/Linux
source .venv/bin/activate
```



### pip

After installing a suitable python 3, make sure you have that python set as your python alias, and run:
```shell
python -m virtualenv .venv
```

Activate this new environment:
```shell
# Windows
./venv/Scripts/activate

# MacOS/Linux
source .venv/bin/activate
```

Install the package:
```shell
pip install -e .
```

## Running

```shell
python -m vr_treadmill
```

> [!WARNING]
> In theory you could run this script without installing as a package but I don't plan to support this so if it doesn't work when you run the main file directly don't complain, just read the readme.

Raw input mode is highly recommended, but I've only built this feature for windows so far.

While running in non-raw input mode, you can press the recenter toggle key to free your mouse for setting up controls. (Default is F9)
