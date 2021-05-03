# pp_dbmanager.py

import sqlite3
from sqlite3 import Connection, Error
from typing import Optional
import logging

from src.pp_order import Order

log = logging.getLogger('log')


class DBManager:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.conn = DBManager.create_connection(file_name=db_name)
        self.cursor = self.conn.cursor()

        # drop_orders_table = 'DROP TABLE IF EXISTS orders'

        # orders = """
        #     CREATE TABLE IF NOT EXISTS orders (
        #         uid TEXT,
        #         session_id TEXT,
        #         pt_id TEXT,
        #         creation_date TIMESTAMP,
        #         side TEXT,
        #         price REAL,
        #         amount REAL,
        #         commission REAL,
        #         status TEXT )
        #         """

        orders_query = self.get_table_creation_query(table='orders')

        # drop before creating the orders table, to ensure a clean new one
        # self.create_table(query=drop_orders_table)
        self.create_table(query=orders_query)

    def __del__(self):
        print('closing cursor and connection...')
        # self.cursor.close()
        self.conn.close()

    def get_table_creation_query(self, table: str) -> str:
        query = f'CREATE TABLE IF NOT EXISTS {table} '
        query += """
                    (
                        uid TEXT,
                        session_id TEXT,
                        pt_id TEXT,
                        creation_date TIMESTAMP,
                        side TEXT,
                        price REAL,
                        amount REAL,
                        commission REAL,
                        status TEXT
                    );
                """
        return query

    def add_order(self, table: str, order: Order) -> None:
        try:
            # c = self.conn.cursor()
            c = self.cursor
            # prepare simple order properties binding
            value_tuple = (
                order.uid,
                order.session_id,
                order.pt_id,
                order.creation,
                order.k_side,
                order.price,
                order.amount,
                order.bnb_commission,
                order.status.name  # note the name property
            )
            # print('add_order(): value: ', value_tuple)
            c.execute(f'INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                      value_tuple)
            self.conn.commit()
        except Error as e:
            log.critical(e)

    def delete_order(self, order: Order, table: str):
        try:
            # identify order by order_id
            c = self.cursor
            c.execute(f'DELETE FROM {table} WHERE uid = ?',
                      (order.uid,))
            self.conn.commit()
        except Error as e:
            log.critical(e)



    def create_table(self, query: str) -> None:
        try:
            # c = self.conn.cursor()
            c = self.cursor
            c.execute(query)
            self.conn.commit()
        except Error as e:
            log.critical(e)

    @staticmethod
    def create_connection(file_name: str) -> Optional[Connection]:
        """create a database connection to the SQLite database
            specified by db_file
        :param file_name: database file
        :return: Connection object or None
        """
        conn = None
        try:
            conn = sqlite3.connect(
                database=file_name,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False
            )
            return conn
        except Error as e:
            log.critical(e)
        return conn
