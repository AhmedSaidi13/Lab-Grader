import psycopg2

conn = psycopg2.connect(
    "host=127.0.0.1 dbname=graderdb user=grader password=grader123 port=5432"
)

print("CONNECTED OK")
conn.close()