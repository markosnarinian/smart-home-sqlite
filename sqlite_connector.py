import sqlite3
from json import loads

config_file = open("config/config.json")
config = loads(config_file.read())
config_file.close()

database = sqlite3.connect(config['database']['database_name'], check_same_thread=False)
cursor = database.cursor()


def execute(command):
    database = sqlite3.connect(config['database']['database_name'], check_same_thread=False)
    cursor = database.cursor()

    return cursor.execute(command)


def fetchall():
    database = sqlite3.connect(config['database']['database_name'], check_same_thread=False)
    cursor = database.cursor()
    
    return cursor.fetchall()
