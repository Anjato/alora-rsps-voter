import json
import pyodbc
from datetime import datetime


def get_connection_string():
    with open("sql_settings.json", "r") as file:
        settings_data = json.load(file)
    return settings_data["Default"]["connection_string"]


def save_data(ip, region, auth, log):
    connection_string = get_connection_string()
    connection = pyodbc.connect(connection_string)
    log.info("Connecting to SQL database")
    try:
        with connection.cursor() as cursor:
            # Check if the auth code already exists for the given IP
            stored_procedure = "{CALL sp_FindDuplicateAuthCodes(?, ?)}"
            cursor.execute(stored_procedure, (ip, auth))
            result = cursor.fetchone()
            duplicate_found = result is not None
            if duplicate_found:
                duplicate_ip, duplicate_auth_code = result
                log.warning(f"Duplicate IP and auth code found: IP={duplicate_ip}, Auth code={duplicate_auth_code}. Skipping data insertion")
                return

            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = (ip, region, auth, current_datetime, 0)

            stored_procedure = "{CALL sp_InsertAuthCode(?, ?, ?, ?, ?)}"
            log.info("Saving data to SQL database")
            cursor.execute(stored_procedure, data)
            connection.commit()

    finally:
        log.info("Closing SQL connection")
        connection.close()
