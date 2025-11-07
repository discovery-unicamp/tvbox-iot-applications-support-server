#!/bin/bash
sudo apt install python3.11-venv
python3 -m venv photoenv
source photoenv/bin/activate
sudo apt-get update
sudo apt-get install -y python3-dev build-essential gfortran pkg-config
sudo apt install -y libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev libtiff5-dev libwebp-dev libharfbuzz-dev libfribidi-dev

pip install -r requirements.txt
chmod +x run_telegrambot_1hour.sh
chmod +x run_telegrambot_10min.sh
chmod +x run_telegrambot_1day.sh