# Braiins OS+ Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Project Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/aleixps/Braiins-OS-HA)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This is a custom integration for Home Assistant that allows you to control and monitor your cryptocurrency miners running **Braiins OS+**. It connects directly to your miner's local API, providing controls and sensors within your Home Assistant dashboard.

## Features

-   **Local Control**: Connects directly to your miner via its local IP address. No cloud services are required.
-   **Detailed Monitoring**: Provides sensor entities for key metrics with a rapid 5-second update interval.
    -   Total hashrate (TH/s).
    -   Real-time power consumption (W) and energy efficiency (J/TH).
    -   Highest chip and board temperatures.
    -   Per-hashboard hashrate, chip temperature, and board temperature.
-   **Simple Controls**: Provides button entities to perform key actions:
    -   Pause and Resume mining operations.
    -   Increment and Decrement the power target.
-   **Robust Authentication**: Automatically handles the renewal of authentication tokens to ensure the connection is always active.


## Prerequisites

-   A miner running a recent version of Braiins OS+.
-   Home Assistant (Version 2023.11.0 or newer).
-   HACS (Home Assistant Community Store) installed and running.

## Installation

This integration is best installed via HACS.

### HACS (Recommended Method)

1.  Navigate to the HACS section in your Home Assistant.
2.  Go to "Integrations", then click the three-dots menu in the top right and select **"Custom repositories"**.
3.  Paste the following URL into the "Repository" field:
    ```
    https://github.com/aleixps/Braiins-OS-HA
    ```
4.  Select **"Integration"** as the category.
5.  Click **"Add"**.
6.  The "Braiins OS+" integration will now be available in HACS. Find it and click **"Install"**.
7.  Restart Home Assistant after the installation is complete.

### Manual Installation

1.  Go to the [latest release](https://github.com/aleixps/Braiins-OS-HA/releases/latest) page of this repository.
2.  Download the `braiins_os_plus.zip` file.
3.  Unzip the file.
4.  Copy the `braiins_os_plus` directory into your Home Assistant `config/custom_components/` directory.
5.  Restart Home Assistant.

## Configuration

Once installed, you can add and configure the integration through the Home Assistant UI.

1.  Go to **Settings** > **Devices & Services**.
2.  Click the **"+ Add Integration"** button in the bottom right.
3.  Search for **"Braiins OS+"**.
4.  In the configuration dialog, enter the following details:
    -   **Miner IP**: The local IP address of your miner (e.g., `192.168.1.159`).
    -   **Username**: The username for your miner's web interface (e.g., `root`).
    -   **Password**: The password for your miner. If you don't have a password, you must still submit the field (leave it blank).
5.  Click **"Submit"**.

The integration will log in and create a new device with all associated entities.

## Entities Created

The integration creates a single device representing your miner, with the following entities.

### Controls

| Entity ID                       | Description                             | Icon                 |
| ------------------------------- | --------------------------------------- | -------------------- |
| `button.increment_power_target` | Increases the power target by 250W.     | `mdi:arrow-up-bold`  |
| `button.decrement_power_target` | Decreases the power target by 250W.     | `mdi:arrow-down-bold`|
| `button.pause_miner`            | Pauses the mining operation.            | `mdi:pause`          |
| `button.resume_miner`           | Resumes the mining operation.           | `mdi:play`           |

### Sensors

Sensors are automatically updated every **5 seconds**.

#### Summary Sensors

These sensors provide an overview of the entire miner.

| Entity ID                   | Description                                                | Unit |
| --------------------------- | ---------------------------------------------------------- | ---- |
| `sensor.total_hashrate`     | Total real-time hashrate of all boards combined.           | TH/s |
| `sensor.miner_consumption`  | Real-time power consumption of the miner.                  | W    |
| `sensor.miner_efficiency`   | Energy efficiency of the miner.                            | J/TH |
| `sensor.chip_temperature`   | The highest temperature of any chip across all hashboards. | °C   |
| `sensor.board_temperature`  | The highest temperature of any board across all hashboards.| °C   |

#### Per-Hashboard Sensors

The following sensors are created for **each** hashboard detected by the miner. The `_n_` in the entity ID will be replaced by the board ID (e.g., `_1_`, `_2_`, etc.).

| Entity ID                           | Description                                       | Unit |
| ----------------------------------- | ------------------------------------------------- | ---- |
| `sensor.hashboard_n_hashrate`       | The real-time hashrate for this specific board.   | TH/s |
| `sensor.hashboard_n_chip_temp`      | Highest chip temperature for this specific board. | °C   |
| `sensor.hashboard_n_board_temp`     | The surface temperature of this specific board.   | °C   |

### Creating an Energy Sensor (kWh)

To track total energy consumption over time and use it in the Home Assistant Energy Dashboard, you need to create a helper sensor that integrates the `Miner Consumption` sensor.

1.  Navigate to **Settings** > **Devices & Services** > **Helpers**.
2.  Click the **"+ Create Helper"** button.
3.  Find and select **"Integration - Riemann sum integral sensor"**.
4.  Fill out the form:
    -   **Input sensor**: Select `sensor.miner_consumption`.
    -   **Name**: Give it a friendly name, like `Miner Energy`.
    -   **Metric prefix**: Select **k** (for kilo).
    -   **Unit of time**: Select **Hours**.
5.  Click **"Create"**.

This will create a new `sensor.miner_energy` entity that tracks total energy usage in kWh, which you can then add to your Energy Dashboard.

## API Reference

This integration is powered by the official Braiins OS+ API. You can find the documentation [here](https://developer.braiins-os.com/latest/openapi.html).

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/aleixps/Braiins-OS-HA/issues) to see if your issue or idea has already been discussed.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
