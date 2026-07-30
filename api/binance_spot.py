import pandas as pd
import requests


class BinanceSpotAPI:

    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol
        self.base_url = "https://api.binance.com/api/v3"

    def get_spot_cvd(self, interval="15m", limit=32):
        """Отримує свічки та розраховує Taker Buy/Sell Delta і CVD (Cumulative Volume Delta)
        за останні N свічок.
        """
        try:
            url = f"{self.base_url}/klines?symbol={self.symbol}&interval={interval}&limit={limit}"
            res = requests.get(url, timeout=5)
            data = res.json()

            records = []
            for item in data:
                timestamp = pd.to_datetime(item[0], unit="ms")
                close = float(item[4])
                total_vol = float(item[5])  # Загальний об'єм свічки в BTC
                taker_buy_vol = float(
                    item[9]
                )  # Покупки по маркету (Taker Buy) в BTC

                # Продажі по маркету = Загальний об'єм - Покупки
                taker_sell_vol = total_vol - taker_buy_vol

                # Дельта свічки в BTC та USD
                delta_btc = taker_buy_vol - taker_sell_vol
                delta_usd = delta_btc * close

                records.append({
                    "timestamp": timestamp,
                    "close": close,
                    "total_vol": total_vol,
                    "taker_buy_vol": taker_buy_vol,
                    "taker_sell_vol": taker_sell_vol,
                    "delta_btc": delta_btc,
                    "delta_usd": delta_usd,
                })

            df = pd.DataFrame(records)
            if not df.empty:
                # Cumulative Volume Delta (Накопичувальна дельта)
                df["cvd_btc"] = df["delta_btc"].cumsum()
                df["cvd_usd"] = df["delta_usd"].cumsum()
            return df
        except Exception as e:
            print(f"Помилка завантаження Spot CVD: {e}")
            return pd.DataFrame()