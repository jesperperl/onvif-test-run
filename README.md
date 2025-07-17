# onvif-testrun

## ONVIF

### Install python packages

```bash
uv sync
```

### Read ONVIF capabilities

```bash
uv run onvif_example.py
```

## RTSP

### Install opencv on mac

```bash
brew install opencv
```

### Compile C++ RSTP program

```bash
g++ -o rtsp_screenshot rtsp_screenshot.cpp `pkg-config --cflags --libs opencv4`
```

### Grab screenshot

```bash
./rtsp_screenshot rtsp://userid:password@192.168.0.252:554/stream1
```
