# smart-home-sqlite
The "certs" folder contains the SSL certification required for encryption of the connection between client & server. (Sensitive data have been removed)

The "config" folder contains the basic server configuration and the devices linked to each user account in JSON format. (Sensitive data have been removed)

The "device_scripts" folder contains the programs that run on the devices or their controllers and listen for commands to execute.

The "templates" folder contains the websites the login page and websites served by "webapp.py" in HTML format.

The "google_home.py" program is the server that forwards incoming commands from Google to the smart device.

The "sqlite_connector.py" is a program that was used to make the transition from a MySQL database to a portable SQLite databse.

The "smarthome.sqlite" is a portable SQLite database that stores user account information, authorization codes, access tokens and refresh tokens.

The "webapp.py" is a webapp that allows users to add, remove and modify smart home devices from a browser (Note: It isn't ready to use yet).
