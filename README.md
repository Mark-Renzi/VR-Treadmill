# VR-Treadmill
script that converts mouse movement into joystick movement for a VR treadmill.
(requires Python3)


to bind the virtual gamepad using steam input, open the script in a text editor and comment out the indicated line. when the bind is set up, uncomment the line and restart the script.

## Install Process

You can install with pip or uv. If you're going to develop, use uv, but it's not required.

### uv
I recommend [astral's uv](https://docs.astral.sh/uv/getting-started/installation/), a fast package manager that can be used as a compatible drop-in for pip. It can take full advantage of the pyproject file for developers.

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

## FUTURE IDEAS

using an openxr library to directly control the game instead of a virtual xbox360 controller
