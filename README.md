# VR-Treadmill
Script that converts mouse movement into joystick movement for a VR treadmill.

This version adds some more features, including sensitivity remapping.

<img width="480" height="434" alt="image" src="https://github.com/user-attachments/assets/0943172c-6350-423d-9f11-d5af8895bde8" />


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

> [!WARNING]
> In theory you could run this script without installing as a package but I don't plan to support this so if it doesn't work when you run the main file directly don't complain, just read the readme.

While running, you can press the recenter toggle key to free your mouse for setting up controls. (Default is F9)