import json
import pyodbc
from datetime import datetime


def get_connection_string():
    with open("sql_settings.json", "r") as file:
        settings_data = json.load(file)
    return settings_data["Default"]["connection_string"]


def save_data(ip, region, auth):
    connection_string = get_connection_string()
    connection = pyodbc.connect(connection_string)

    try:
        with connection.cursor() as cursor:
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = (ip, region, auth, current_datetime, 0)

            stored_procedure = "{CALL sp_InsertAuthCode(?, ?, ?, ?, ?)}"
            cursor.execute(stored_procedure, data)
            connection.commit()

    finally:
        connection.close()
