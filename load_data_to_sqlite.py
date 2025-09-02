import sqlite3
import os
import csv

# Define the folder and database file name
folder_name = "sqlite"
db_file = os.path.join(folder_name, "customer_travel.db")

# Create the folder if it doesn't exist
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")

# Connect to the SQLite database (this creates the file if it doesn't exist)
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

print(f"Database '{db_file}' created successfully.")

# Close the connection
conn.close()


# 1. Connect to SQLite database (or create it if it doesn’t exist)

conn = sqlite3.connect(db_file)

cursor = conn.cursor()
 
# 2. Create a table (adjust columns to match your CSV)

cursor.execute("""

CREATE TABLE IF NOT EXISTS customerdata (
	Booking_ID	INTEGER,
	DepIATAcode	TEXT,
	departureLocation	TEXT,
	DestIATAcode	TEXT,
	destinationLocation	TEXT,
	cabinClass	TEXT,
	booking_date	TEXT,
	departure_date	TEXT,
	Nationality	TEXT,
	Traveler_name	TEXT,
	Traveler_age	INTEGER,
	Traveler_Id	INTEGER,
	Traveler_Email	TEXT  
)

""")
 
# 3. Open CSV file and insert rows

with open("csv/customer_travel_data.csv", "r", encoding="utf-8") as file:

    reader = csv.reader(file)

    headers = next(reader)  # Skip header row, remove if no header

    for row in reader:

        cursor.execute("INSERT INTO customerdata (Booking_ID, DepIATAcode,departureLocation,DestIATAcode,destinationLocation,cabinClass,booking_date,departure_date,Nationality,Traveler_name,Traveler_age,Traveler_Id,Traveler_Email) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
 
# 4. Commit and close

conn.commit()

conn.close()
