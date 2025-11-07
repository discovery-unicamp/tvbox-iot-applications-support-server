# 🛰️ tvbox-iot-applications-support-server


## ✅ Requirements

- Go 1.24+
- Python 3.11
- Bash shell
- `sudo` permissions
- Linux System

## 📦 Modules

  - [1. `parking_spot_api`](#1-parking_spot_api)
  - [2. `totem_update_server`](#2-totem_update_server)
  - [3. `totem_update_cli`](#3-totem_update_cli)
  - [4. `tvbox_monitoring`](#4-tvbox_monitoring)
  - [5. `health_checks`](#5-health_checks)
  - [6. `system_config`](#6-system_config)
  - [7. `img_preconfig`](#7-img_preconfig)

---



### 1. `parking_spot_api`

**Purpose:**
Provides an API to monitor and control parking spots via InfluxDB. Supports authenticated control endpoints.

**Features:**

* REST endpoints:

  * `/last_value`, `/last_timestamp`, `/last_spots` — data queries
  * `/turnOn`, `/turnOff` — authenticated toggles
* Heartbeat logging to InfluxDB
* Basic Auth protection
* Chi router with middleware and .env configuration

**Run:**

```bash
cd parking_spot_api
make build-tx2
./bin/parkingLotServer
```

---

### 2. `totem_update_server`

**Purpose:**
Acts as an OTA (Over-The-Air) firmware update server for the ESP8266 device.

**Features:**

* Serves and stores firmware binaries
* `/upload` — accepts new firmware versions
* `/update` — provides latest firmware if a newer version exists
* `/` — lists all available versions

**Run:**

```bash
cd totem_update_server
make build-tx2
./bin/totemUpdateServer
```

**Default Port:** `:8002`

---

### 3. `totem_update_cli`

**Purpose:**
Command-line interface for building and uploading firmware to devices or servers.

**Features:**

* Builds PlatformIO projects
* Uploads via USB (`--local`) or HTTP to OTA server
* Manages credentials cache via `totemUpdateCache.json`

**Usage Example:**

```bash
cd totem_update_cli
make build
```

After copying the generated binary to the Platformio project, you can run:
```bash
./totemUpdateCLI           # Upload via server
./totemUpdateCLI --local   # Direct USB upload
```

---

### 4. `tvbox_monitoring`

**Purpose:**
Monitors CPU, temperature, and memory metrics from TVBox devices.
Logs data locally in Redis and periodically uploads it to InfluxDB.

**Features:**

* Collects system stats every minute
* Uploads aggregated data every 15 minutes
* Uses Redis as a local buffer
* Fully environment-configurable (`.env`)

**Run:**

```bash
cd tvbox_monitoring
make build-tx2
./bin/tvboxPerformance
```

---

### 5. `health_checks`

**Purpose:** Checks periodically for InfluxDB entries for both parking lots and totem heartbeats. 
If the time period since the last record reaches a minimum threshold, send a alert message through a Telegram Bot.



**Run:**

``` bash
chmod +x config_bots.sh
./config_bots.sh
```

More information can be found inside the [health_checks folder](./health_checks/README.md)

---

### 6. `system_config`

**Purpose:**
Automates the deployment and configuration of the entire system on a Linux server.

**Key script:** `setup.sh`

**What it does:**

* Updates and installs system packages (NGINX, Redis)
* Configures NGINX and systemd services
* Copies binaries to `/root/servers/`
* Enables and starts services
* Applies systemd overrides
* Reboots system

**Run:**

```bash
cd system_config
sudo ./setup.sh
```

---

### 7. `img_preconfig`

**Purpose:**
Preconfigures OS image files before flashing onto devices.
Automates Wi-Fi, locale, and provisioning setup directly inside `.img` files.

**Run:**

```bash
cd img_preconfig
./configure_img.sh
```

**Requires:**
`.env` file with Wi-Fi and user parameters.
