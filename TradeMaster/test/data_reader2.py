import psycopg2
from psycopg2 import sql

# Define connection parameters
db_host = "62.72.42.9"
db_port = 8812  # Default PostgreSQL port
db_name = "admin"
db_user = "admin"
db_password = "2Cents#101"

# Establish a connection

conn = psycopg2.connect(
    host=db_host,
    port=db_port,
    dbname=db_name,
    user=db_user,
    password=db_password
)
print("Database connection established.")

# Create a cursor object to execute queries
cursor = conn.cursor()

# Create SQL query to pull all records from the AAPL table
query = sql.SQL("SELECT * FROM {}").format(sql.Identifier('AAPL'))

# Execute the query
cursor.execute(query)

# Fetch all records from the table
records = cursor.fetchall()
print("records fetched")
print(len(records))

