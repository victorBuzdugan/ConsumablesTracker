# Description
This is an app for checking an inventory of consumables. It can be used at home or at work. Anybody can be assigned a list of consumables to keep track of. The process can be started by one of the admins either after one user requests it or at a time interval. The inventory can be unlocked either for each user or for all users at the same time.

## Home use case
There are a lot of consumables that need to be tracked at home and easy to forget about. Starting with house consumables (toilet paper, detergent, batteries, light bulbs), kitchen and food related consumables (flour, sugar), kids related (crayons, paper) and personal consumables (toothpaste, soap). Even kids can be assigned a part of the list.

## Work use case
Based on the business, there can be a lot of consumables that you would want to track. Starting with basic things like paper, printer cartridges and office consumables, coffee, sugar and finishing with screws or filters or some other business specifics consumables.

# Live demo

## Website
Follow <https://victorb.eu.pythonanywhere.com> for a working demo.

The database resets every day at 05:00 UTC (08:00 EEST Romania time).

## Login credentials
Login credentials:
| username 	| password 	|
|:--------:	|:--------:	|
|   user1  	| Q!111111 	|
|   user2  	| Q!222222 	|
|   user3  	| Q!333333 	|
|   user4  	| Q!444444 	|
|   user5  	| Q!555555 	|

# Installation

## Install
Clone the [repository](https://github.com/victorBuzdugan/ConsumablesTracker) from GitHub.

## Post install
After cloning install all dependencies from `requirements.txt`

You also have to provide a `.env` file for Flask secret key.
Create a new file named `.env` in the root folder:
```python
# Optional Flask debug
# FLASK_DEBUG="true"
FLASK_SECRET_KEY="replace_this_with_secret_key"
```
You can follow the guide in the [official documentation](https://flask.palletsprojects.com/en/2.3.x/quickstart/#sessions) of Flask in order to generate a good `SECRET_KEY`.

## Database
The project comes with a demo `inventory.db` SQLite database.

Because of the 'closed' environment nature of the app (users need to be approved by an admin after registration), if you edit the database with [sqlite3 command line shell](https://sqlite.org/cli.html) or a software like [DB Browser for SQLite](https://sqlitebrowser.org) be careful to **leave at least one admin user** in the database.

## Login credentials
Login credentials for demo `inventory.db` SQLite database are the same as for the demo website.

# Help
Take a look at the [wiki page](https://github.com/victorBuzdugan/ConsumablesTracker/wiki).