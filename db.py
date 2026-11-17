import pymysql
from pymysql.cursors import DictCursor
from config import Config

def get_db_connection():
    """Establishes and returns a connection to MySQL database."""
    conn_params = {
        'host': Config.MYSQL_HOST,
        'user': Config.MYSQL_USER,
        'password': Config.MYSQL_PASSWORD,
        'database': Config.MYSQL_DB,
        'port': Config.MYSQL_PORT,
        'cursorclass': DictCursor,
        'autocommit': False,
        'connect_timeout': 10
    }
    if Config.MYSQL_SSL:
        conn_params['ssl'] = {'ssl_mode': 'REQUIRED'}
    return pymysql.connect(**conn_params)

def query_db(query, args=(), one=False):
    """Executes a SELECT query and returns results as dicts."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

def execute_db(query, args=(), commit=True):
    """Executes an INSERT, UPDATE, or DELETE query and returns the last inserted row ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            last_id = cursor.lastrowid
        if commit:
            conn.commit()
        return last_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
