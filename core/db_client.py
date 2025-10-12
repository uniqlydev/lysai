import dotenv
import psycopg2
import os


dotenv.load_dotenv()


def get_connection(): 
    """
    Establish and return a connection to the PostgreSQL database using environment variables.
    """
    conn_params = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", 5432),
        "dbname": os.getenv("POSTGRES_DB", "pagila-db"),
        "user": os.getenv("POSTGRES_USER", "pagila"),
        "password": os.getenv("POSTGRES_PASSWORD", "pagila"),
    }


    # Establish and return the database connection
    return psycopg2.connect(**conn_params)



def get_client():
    """
    Get a database connection and return a cursor.
    """

    conn = get_connection()
    return conn, conn.cursor()