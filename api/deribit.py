from datetime import datetime
import pandas as pd
import requests


class DeribitAPI:

    def __init__(self):
        self.base_url = "https://www.deribit.com/api/v2"

    def get_btc_price(self) -> float:
        """Получение текущей спотовой цены BTC."""
        try:
            url = f"{self.base_url}/public/get_index_price"
            params = {"index_name": "btc_usd"}
            res = requests.get(url, params=params, timeout=10).json()
            return float(res.get("result", {}).get("index_price", 0.0))
        except Exception as e:
            print(f"Ошибка при получении цены BTC: {e}")
            return 0.0

    def get_options_book(self, currency: str = "BTC") -> pd.DataFrame:
        """Получение книги опционов (Open Interest, IV, Strike и т.д.)."""
        try:
            url = f"{self.base_url}/public/get_book_summary_by_currency"
            params = {"currency": currency, "kind": "option"}
            res = requests.get(url, params=params, timeout=10).json()

            items = res.get("result", [])
            if not items:
                return pd.DataFrame()

            data = []
            now = datetime.utcnow()

            for item in items:
                name = item.get("instrument_name", "")
                parts = name.split("-")
                if len(parts) < 4:
                    continue

                exp_str = parts[1]
                strike = float(parts[2])
                opt_type = "call" if parts[3] == "C" else "put"

                try:
                    exp_date = datetime.strptime(exp_str, "%d%b%y")
                except Exception:
                    continue

                dte = max((exp_date - now).total_seconds() / 86400.0, 0.001)

                data.append(
                    {
                        "instrument_name": name,
                        "strike": strike,
                        "type": opt_type,
                        "open_interest": float(
                            item.get("open_interest", 0.0)
                        ),
                        "iv": float(item.get("mark_iv", 55.0)) / 100.0,
                        "mark_iv": float(item.get("mark_iv", 55.0)),
                        "expiration_str": exp_str,
                        "expiration_date": exp_date,
                        "dte": dte,
                    }
                )

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Ошибка при получении опционов: {e}")
            return pd.DataFrame()

    def get_block_trades(
        self, currency: str = "BTC", min_usd_val: float = 50000.0
    ) -> pd.DataFrame:
        """Получение крупных сделок (Block Trades / OTC) китов с Deribit."""
        try:
            url = f"{self.base_url}/public/get_last_trades_by_currency"
            params = {"currency": currency, "kind": "option", "count": 100}
            res = requests.get(url, params=params, timeout=10).json()

            trades = res.get("result", {}).get("trades", [])
            if not trades:
                return pd.DataFrame()

            data = []
            for t in trades:
                amount = t.get("amount", 0.0)
                price = t.get("index_price", 0.0)
                trade_usd = amount * price

                if trade_usd >= min_usd_val:
                    dt = datetime.fromtimestamp(
                        t.get("timestamp", 0) / 1000.0
                    )
                    data.append(
                        {
                            "Время": dt.strftime("%H:%M:%S"),
                            "Инструмент": t.get("instrument_name"),
                            "Направление": (
                                "BUY 🟢"
                                if t.get("direction") == "buy"
                                else "SELL 🔴"
                            ),
                            "Размер (BTC)": amount,
                            "Сумма ($)": f"${trade_usd:,.0f}",
                            "IV (%)": f"{t.get('iv', 0):.1f}%",
                            "Тип": (
                                "Block OTC"
                                if t.get("trade_seq") == 0
                                else "Standard"
                            ),
                        }
                    )

            return pd.DataFrame(data)
        except Exception as e:
            print(f"Ошибка при получении Block Trades: {e}")
            return pd.DataFrame()

    def get_futures_ticker(
        self, instrument_name: str = "BTC-PERPETUAL"
    ) -> dict:
        """Получение тикера фьючерса для Basis & Funding."""
        try:
            url = f"{self.base_url}/public/ticker"
            params = {"instrument_name": instrument_name}
            res = requests.get(url, params=params, timeout=10).json()

            result = res.get("result", {})
            if result:
                return {
                    "mark_price": float(result.get("mark_price", 0.0)),
                    "index_price": float(result.get("index_price", 0.0)),
                    "funding_8h": float(result.get("current_funding", 0.0))
                    * 100.0,
                }
        except Exception as e:
            print(f"Ошибка при получении фьючерсного тикера: {e}")

        return {"mark_price": 0.0, "index_price": 0.0, "funding_8h": 0.0}