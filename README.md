# Braiins OS+ Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Project Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/aleixps/Braiins-OS-HA)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This is a custom integration for Home Assistant that allows you to control and monitor your cryptocurrency miners running **Braiins OS+**. It connects directly to your miner's local API, providing simple controls within your Home Assistant dashboard.

## Features

-   **Local Control**: Connects directly to your miner via its local IP address. No cloud services are required.
-   **Simple Controls**: Provides button entities to perform key actions:
    -   Pause and Resume mining operations.
    -   Increment and Decrement the power target by 250W.
-   **Robust Authentication**: Automatically handles the renewal of authentication tokens to ensure the connection is always active.

## Screenshot

<!-- It is highly recommended to replace this with a real screenshot of the device entities in Home Assistant -->
![image](https://user-images.githubusercontent.com/12345/67890.png)

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

The integration will log in, retrieve an authentication token, and create a new device with four button entities.

## Entities

This integration creates the following button entities:

| Entity                        | Description                             | Icon                 |
| ----------------------------- | --------------------------------------- | -------------------- |
| `button.increment_power_target` | Increases the power target by 250W.     | `mdi:arrow-up-bold`  |
| `button.decrement_power_target` | Decreases the power target by 250W.     | `mdi:arrow-down-bold`|
| `button.pause_miner`            | Pauses the mining operation.            | `mdi:pause`          |
| `button.resume_miner`           | Resumes the mining operation.           | `mdi:play`           |

## API Reference

This integration is powered by the official Braiins OS+ API. You can find the documentation [here](https://developer.braiins-os.com/latest/openapi.html).

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/aleixps/Braiins-OS-HA/issues) to see if your issue or idea has already been discussed.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
