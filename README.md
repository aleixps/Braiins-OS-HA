Braiins OS+ Integration for Home Assistant

![alt text](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)


![alt text](https://img.shields.io/badge/Maintained%3F-yes-green.svg)


![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)

This is a custom integration for Home Assistant that allows you to control and monitor your cryptocurrency miners running Braiins OS+. It connects directly to your miner's local API, providing simple controls within your Home Assistant dashboard.
Features

    Local Control: Connects directly to your miner via its local IP address. No cloud services are required.

    Simple Controls: Provides button entities to perform key actions:

        Pause and Resume mining operations.

        Increment and Decrement the power target by 250W.

    Robust Authentication: Automatically handles the renewal of authentication tokens to ensure the connection is always active.

Screenshot
<!-- It is highly recommended to replace this with a real screenshot of the device entities in Home Assistant -->

![alt text](https://user-images.githubusercontent.com/12345/67890.png)

Prerequisites

    A miner running a recent version of Braiins OS+.

    Home Assistant (Version 2023.11.0 or newer).

    HACS (Home Assistant Community Store) installed and running.

Installation

This integration is best installed via HACS.
HACS (Recommended Method)

    Navigate to the HACS section in your Home Assistant.

    Go to "Integrations", then click the three-dots menu in the top right and select "Custom repositories".

    Paste the following URL into the "Repository" field:
    code Code

    IGNORE_WHEN_COPYING_START
    IGNORE_WHEN_COPYING_END

        
    https://github.com/aleixps/Braiins-OS-HA

      

    Select "Integration" as the category.

    Click "Add".

    The "Braiins OS+" integration will now be available in HACS. Find it and click "Install".

    Restart Home Assistant after the installation is complete.

Manual Installation

    Go to the latest release page of this repository.

    Download the braiins_os_plus.zip file.

    Unzip the file.

    Copy the braiins_os_plus directory into your Home Assistant config/custom_components/ directory.

    Restart Home Assistant.

Configuration

Once installed, you can add and configure the integration through the Home Assistant UI.

    Go to Settings > Devices & Services.

    Click the "+ Add Integration" button in the bottom right.

    Search for "Braiins OS+".

    In the configuration dialog, enter the following details:

        Miner IP: The local IP address of your miner (e.g., 192.168.1.159).

        Username: The username for your miner's web interface (e.g., root).

        Password: The password for your miner. If you don't have a password, you must still submit the field (leave it blank).

    Click "Submit".

The integration will log in, retrieve an authentication token, and create a new device with four button entities.
Entities

This integration creates the following button entities:
Entity	Description	Icon
button.increment_power_target	Increases the power target by 250W.	mdi:arrow-up-bold
button.decrement_power_target	Decreases the power target by 250W.	mdi:arrow-down-bold
button.pause_miner	Pauses the mining operation.	mdi:pause
button.resume_miner	Resumes the mining operation.	mdi:play
API Reference

This integration is powered by the official Braiins OS+ API. You can find the documentation here.
Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page to see if your issue or idea has already been discussed.
License

This project is licensed under the MIT License. See the LICENSE file for details.
