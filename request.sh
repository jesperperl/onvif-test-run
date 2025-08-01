#!/bin/bash

python3 onvif_request.py > request.xml
curl --silent -X POST --header 'Content-Type: text/xml; charset=utf-8' -d @request.xml 'http://192.168.0.252:2020/onvif/device_service' | xmllint --format -
