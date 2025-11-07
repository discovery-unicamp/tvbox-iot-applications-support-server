# Health Checks Bots - Setup Guide

This project uses Python virtual environments and several system
dependencies to run Telegram bots on different schedules.

------------------------------------------------------------------------

## 🚀 Installation


### 1. Run the setup script 

```

Run `config_bots.sh` :

``` bash
chmod +x config_bots.sh
./config_bots.sh
```

------------------------------------------------------------------------

## 📦 What the setup does

### ✅ Creates a Python virtual environment

All Python packages stay isolated inside `photoenv/`.

### ✅ Installs required system packages

### ✅ Installs Python dependencies

Everything listed in `requirements.txt`.

### ✅ Makes the bot runners executable

-   `run_telegrambot_1hour.sh`\
-   `run_telegrambot_10min.sh`\
-   `run_telegrambot_1day.sh`

These can then be executed manually or scheduled via `cron` or even `supervisor`.

------------------------------------------------------------------------

## ▶️ Running the bots manually

Activate the virtual environment:

``` bash
source photoenv/bin/activate
```

Run any of the bots manually:

``` bash
./run_telegrambot_1hour.sh
./run_telegrambot_10min.sh
./run_telegrambot_1day.sh
```

------------------------------------------------------------------------

## ⏱️ Optional: Add to crontab

Open the cron editor:

``` bash
sudo crontab -e
```

Example entries:

``` cron
*/10 * * * * /path/to/run_telegrambot_10min.sh
0 * * * * /path/to/run_telegrambot_1hour.sh
0 0 * * * /path/to/run_telegrambot_1day.sh
```

## To reboot every 6 hours, add:


``` cron
@reboot sleep 21600 && sudo reboot
```

------------------------------------------------------------------------

For details on how to set InfluxDB and the telegram bot tokens please refer to the configuration setup at [our other repoitory](https://github.com/discovery-unicamp/smartparking_unicamp/tree/main/software/influx).