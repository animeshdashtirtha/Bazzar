import mysql.connector

try:
    # Connect to the server
    connection = mysql.connector.connect(
        host="localhost",
        user="root",         # Default user
        password="YOUR_PASSWORD_HERE", 
        database="bazzar_db"
    )

    if connection.is_connected():
        print("Successfully connected to MySQL!")
        
except Exception as e:
    print(f"Error: {e}")

finally:
    if 'connection' in locals() and connection.is_connected():
        connection.close()