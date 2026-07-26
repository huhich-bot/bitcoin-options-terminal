import requests
import pandas as pd


class DeribitAPI:
    BASE_URL = "https://www.deribit.com/api/v2"

    def __init__(self):
        self.session = requests.Session()

    def get_btc_price(self):
        """Поточна ціна BTC"""
        url = f"{self.BASE_URL}/public/get_index_price"
        params = {"index_name": "btc_usd"}

        r = self.session.get(url, params=params, timeout=10)
        r.raise_for_status()

        data = r.json()["result"]

        return float(data["index_price"])

    def get_instruments(self):
        """Отримати список усіх BTC-опціонів"""

        url = f"{self.BASE_URL}/public/get_instruments"

        params = {
            "currency": "BTC",
            "kind": "option",
            "expired": "false"
        }

        r = self.session.get(url, params=params, timeout=20)
        r.raise_for_status()

        return r.json()["result"]

    def get_orderbook(self, instrument_name):
        """Отримати дані конкретного опціону"""

        url = f"{self.BASE_URL}/public/get_order_book"

        params = {
            "instrument_name": instrument_name
        }

        r = self.session.get(url, params=params, timeout=20)
        r.raise_for_status()

        return r.json()["result"]

    def load_options(self):

        instruments = self.get_instruments()

        rows = []

        for ins in instruments:

            try:

                ob = self.get_orderbook(
                    ins["instrument_name"]
                )

                rows.append({

                    "instrument": ins["instrument_name"],

                    "expiry": ins["expiration_timestamp"],

                    "strike": ins["strike"],

                    "type": ins["option_type"],

                    "open_interest": ob["open_interest"],

                    "mark_price": ob["mark_price"],

                    "mark_iv": ob["mark_iv"],

                    "bid": ob["best_bid_price"],

                    "ask": ob["best_ask_price"]

                })

            except Exception as e:

                print(
                    f"Помилка {ins['instrument_name']}: {e}"
                )

        df = pd.DataFrame(rows)

        return df