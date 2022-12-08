#!./env/lib/python3.11
import psycopg2
import psycopg2.extras
import os
from handy import *


# ----------------------LOGGING-Config--------------------#
import logging
import traceback
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s:%(created)f:%(filename)s:%(levelname)s:%(funcName)s:%(lineno)d:%(message)s")
file_handler = logging.FileHandler(os.path.abspath(f"LOGS/{__name__}.log"))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# --------------------------------------------------------#

DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

with conn:
    # Patreon
    cur.execute("""CREATE TABLE IF NOT EXISTS Patreon(
            member_id BIGINT,
            tier_title TEXT,
            status TEXT,
            pledge_amount BIGINT,
            pledge_created_at TEXT,
            total_historical_amount BIGINT
            )""")
    # Auth
    cur.execute("""CREATE TABLE IF NOT EXISTS Auth(
            member_id BIGINT,
            replicate_token TEXT
            )""")
    # Credit
    cur.execute("""CREATE TABLE IF NOT EXISTS Credit(
            member_id BIGINT,
            credit BIGINT
            )""")
    # Image
    cur.execute("""CREATE TABLE IF NOT EXISTS Image(
            member_id BIGINT,
            prompt TEXT,
            neg_prompt TEXT,
            model TEXT,
            runtime REAL,
            time_int BIGINT
            )""")


# -------------------------------------------------------#
def reconnect(database_action):
    def wrap(*args, **kwargs):
        global conn, cur
        try:
            return database_action(*args, **kwargs)
        except Exception as e:
            if isinstance(e, psycopg2.InterfaceError):
                logger.warning(f"{e} reconnecting...")
                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                return database_action(*args, **kwargs)
            else:
                logger.exception(f"args {args}, kwargs {kwargs}" + '\n' + ''.join(traceback.format_exception(e)))
    return wrap
# -------------------------------------------------------#


@reconnect
async def get_patreon(member: int):
    cur.execute("SELECT * FROM Patreon WHERE member_id = %s", (member,))
    data = cur.fetchone()
    if data is not None:
        return dict(data)


@reconnect
async def insert_patreon(data: dict):
    with conn:
        cur.execute("INSERT INTO Patreon (member_id, tier_title, status, pledge_amount, pledge_created_at, total_historical_amount) VALUES (%s, %s, %s, %s, %s, %s)", (data['discord'], data['tier_title'], data['status'], data['pledge_amount'], data['pledge_created_at'], data['total_historical_amount_cents']))
        cur.execute("INSERT INTO Credit (member_id, credit) VALUES (%s, %s)", (data['discord'], calculate_credit(data['pledge_amount'])))


@reconnect
async def add_credit(member: int, credit: int):
    with conn:
        cur.execute("UPDATE Credit SET credit = credit + %s WHERE member_id = %s", (credit, member))


@reconnect
async def update_patreon(data: dict):
    with conn:
        cur.execute("UPDATE Patreon SET tier_title=%s, status=%s, pledge_amount=%s, pledge_created_at=%s, total_historical_amount=%s WHERE member_id=%s", (data['tier_title'], data['status'], data['pledge_amount'], data['pledge_created_at'], data['total_historical_amount_cents'], data['discord']))


@reconnect
async def get_token(member: int):
    cur.execute("SELECT replicate_token FROM Auth WHERE member_id=%s", (member,))
    data = cur.fetchone()
    if data is not None:
        return dict(data)


@reconnect
async def insert_token(member: int, token: str):
    with conn:
        cur.execute("DELETE FROM Auth WHERE member_id=%s", (member,))
        cur.execute("INSERT INTO Auth (member_id, replicate_token) VALUES (%s, %s)", (member, token))


@reconnect
async def remove_token(member: int):
    with conn:
        cur.execute("DELETE FROM Auth WHERE member_id=%s", (member,))
