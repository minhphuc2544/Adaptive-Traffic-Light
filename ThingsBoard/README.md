# Setup ThingsBoard's Devices and Dashboard guide

## Runing the ThingsBoard as a Docker Container
```bash
cd ThingsBoard
docker compose up -d
```

## Login to the ThingsBoard WebUI
Access the website at [http://your-ip-address:9090](http://your-ip-address:9090) and login with the default credentials:
- Default username: `tenant@thingsboard.org`
- Default password: `tenant`

## Create Devices on 4 directions at crossroad
1. Go to `Entities` → `Devices` on the website's toolbar
2. Click `+` icon → `Add new device`
3. Enter `Name` (East Device, West Device, South Device, North Device)
4. Click `Add`

**Note: Remember to copy 4 device's API Keys in order to put it in the `.env` file in the root folder**

## Import Dashboard as a JSON file
1. Go to `Dashboard` on the website's toolbar
2. Click `+` icon → `Import dashboard`
3. Select the `traffic_monitor.json` file on the same folder
4. Click `Import`