from datetime import datetime
import dask.dataframe as dd
import pandas as pd
from sqlalchemy import create_engine
import psycopg2

db_host = "62.72.42.9"
db_port = 8812  # Default PostgreSQL port
db_name = "qdb"
db_user = "admin"
db_password = "2Cents#101"

conn = psycopg2.connect(
    host=db_host,
    port=db_port,
    dbname=db_name,
    user=db_user,
    password=db_password
)
print("Database connection established.")
a=datetime.now()
df = dd.from_pandas(pd.read_sql_query("SELECT * FROM AAPL", conn), npartitions=10)
b=datetime.now()
print("time taken:-",b-a)
print(df)