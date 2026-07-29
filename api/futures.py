import pandas as pd
import requests


class BinanceFuturesAPI:

    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol
        self.base_url = "https://fapi.binance.com/fapi/v1"

    def get_futures_cvd(self, interval="15m", limit=32):
        """Отримує Taker Buy/Sell з ф'ючерсів Binance та рахує CVD."""
        try:
            url = f"{self.base_url}/klines?symbol={self.symbol}&interval={interval}&limit={limit}"
            res = requests.get(url, timeout=5)
            data = res.json()

            records = []
            for item in data:
                timestamp = pd.to_datetime(item[0], unit="ms")
                close = float(item[4])
                total_vol = float(item[5])
                taker_buy_vol = float(item[9])

                taker_sell_vol = total_vol - taker_buy_vol
                delta_btc = taker_buy_vol - taker_sell_vol
                delta_usd = delta_btc * close

                records.append({
                    "timestamp": timestamp,
                    "close": close,
                    "delta_usd": delta_usd,
                })

            df = pd.DataFrame(records)
            if not df.empty:
                df["cvd_usd"] = df["delta_usd"].cumsum()
            return df
        except Exception as e:
            print(f"Помилка завантаження Futures CVD: {e}")
            return pd.DataFrame()