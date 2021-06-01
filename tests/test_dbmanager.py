# test_dbmanager.py

import unittest
import os
from binance import enums as k_binance

from src.pp_order import Order, OrderStatus
from polaris_old.pp_dbmanager import DBManager

TEST_DATABASE = 'test.db'


class TestDBManager(unittest.TestCase):
    def setUp(self) -> None:
        try:
            os.remove(TEST_DATABASE)
        except IOError as e:
            print(e)
        print('cwd: ', os.getcwd())

        self.dbm = DBManager(db_name=TEST_DATABASE, order_tables=['orders'])

        self.order = Order(
            session_id='S_20210501_2008',
            order_id='ORDER_ID',
            pt_id='PT_ID',
            k_side=k_binance.SIDE_BUY,
            price=50_000.0,
            amount=1.0,
        )
        self.order_2 = Order(
            session_id='S_20210501_2008',
            order_id='OR_000001',
            pt_id='PT_000001',
            k_side=k_binance.SIDE_SELL,
            price=60_000.88,
            amount=1.0876548765,
            uid='0123456789abcdef'
        )

    def test_get_table_creation_query(self):
        print(self.dbm.get_table_creation_query(table='orders'))

    def test_add_order(self):
        table = 'orders'
        self.dbm.add_order(table=table, order=self.order)
        c = self.dbm.conn.cursor()
        rows = c.execute(f'SELECT * FROM {table};').fetchall()
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual(OrderStatus.MONITOR.name, row[8])

    def test_delete_order(self):
        table = 'orders'
        self.dbm.add_order(table=table, order=self.order)
        self.dbm.add_order(table=table, order=self.order_2)
        self.dbm.delete_order(table=table, order=self.order)
        c = self.dbm.conn.cursor()
        rows = c.execute(f'SELECT * FROM {table};').fetchall()
        self.assertEqual(1, len(rows))
        self.assertEqual('0123456789abcdef', rows[0][0])


    def tearDown(self) -> None:
        self.dbm.conn.close()
