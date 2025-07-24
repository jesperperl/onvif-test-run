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

### Suppress log messages from ffmpg

```bash
export OPENCV_FFMPEG_LOGLEVEL=8
```

### Grab screenshot

```bash
./rtsp_screenshot rtsp://userid:password@192.168.0.252:554/stream1
```

### Display stream

Save screenshot with 's' and quit stream with 'q'

```bash
./rtsp_screenshot rtsp://userid:password@192.168.0.252:554/stream1 --display
```

### Onvif server

#### C++

```bash
g++ -std=c++11 -pthread -o onvif_server onvif_server.cpp
./onvif_server
```

Access services at:

* Device Service: http://localhost:8080/onvif/device_service
* Media Service: http://localhost:8080/onvif/media_service
* PTZ Service: http://localhost:8080/onvif/ptz_service

#### Python

```bash
uv sync
uv run python onvif_server.py
```

Available endpoints:
* Device Service: http://localhost:8000/onvif/device_service
* Media Service: http://localhost:8000/onvif/media_service
* PTZ Service: http://localhost:8000/onvif/ptz_service