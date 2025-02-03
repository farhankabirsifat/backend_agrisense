import mysql.connector
from fastapi import HTTPException
import os

# MySQL database configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "crop_and_fertilizer_recommendation_db",
    "port": 4306,
}

# db_config = {
#     "host": "bepjd6wyxkg8i157jrtn-mysql.services.clever-cloud.com",
#     "user": "ux3pl9tv87elba36",
#     "password": "nQjG2mZ3xUSIdLePpbKg",
#     "database": "bepjd6wyxkg8i157jrtn",
#     "port": 3306,
# }

# db_config = {
#     "host": os.getenv("DB_HOST"),
#     "user": os.getenv("DB_USER"),
#     "password": os.getenv("DB_PASSWORD"),
#     "database": os.getenv("DB_NAME"),
#     "port": int(os.getenv("DB_PORT", 3306)),
# }

# Function to connect to the database
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
