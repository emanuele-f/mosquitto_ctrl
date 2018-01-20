# mosquitto_ctrl
A controller for an MQTT device using the mosquitto MQTT server.

I use this script to control a sonoff (esp8266) device.

- After the user powers the device on, automatic power management is enabled
- After the user powers the device off, automatic power management is disabled
- When automatic power management is enabled, the device will stay on for 40 minutes. Then it is powered off for 20 minutes, then again on.
- Device should power off at 8:00 am (and automatic power management disabled)

# Configuration file
A file `mqtt_cfg.py` should be created with MQTT credentials:

```
username="mqtt_username"
password="mqtt_password"
```
