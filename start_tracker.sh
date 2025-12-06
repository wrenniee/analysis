#!/bin/bash
pkill -f tracker_backend.py 2>/dev/null
sleep 1
python3 tracker_backend.py
