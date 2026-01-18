import os
from dotenv import load_dotenv

LOGS_DB_CONFIG = {
    "server": os.getenv("LOGS_DB_SERVER"),
    "database": os.getenv("LOGS_DB_NAME"),
    "username": os.getenv("LOGS_DB_USERNAME"),
    "password": os.getenv("LOGS_DB_PASSWORD"),
    "driver": "ODBC Driver 18 for SQL Server"
}