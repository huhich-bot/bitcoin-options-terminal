import pandas as pd
import numpy as np

class LiquidationCalculator:
    @staticmethod
    def find_pivots(df: pd.DataFrame, window: int = 4):
        """Знаходить локальні максимуми та мінімуми (свінги)."""
        if df.empty or len(df) < window * 2 + 1:
            return [], []

        highs = []
        lows = []
        
        for i in range(window, len(df) - window):
            sub = df.iloc[i - window : i + window + 1]
            current_high = df.iloc[i]['high']
            current_low = df.iloc[i]['low']

            if current_high == sub['high'].max():
                highs.append(current_high)
            if current_low == sub['low'].min():
                lows.append(current_low)

        return list(set(highs)), list(set(lows))

    @staticmethod
    def calculate_liquidation_levels(btc_price: float, df_ohlcv: pd.DataFrame, selected_leverages: list) -> list:
        if df_ohlcv.empty or btc_price == 0:
            return []

        # Беремо останні 150 свічок для пошуку актуальних ліквідацій
        df_recent = df_ohlcv.tail(150).copy()
        highs, lows = LiquidationCalculator.find_pivots(df_recent, window=4)

        lev_ratios = {
            50: 0.02,  # 2% рух
            20: 0.05,  # 5% рух
            10: 0.10   # 10% рух
        }

        raw_levels = []

        for lev in selected_leverages:
            ratio = lev_ratios.get(lev, 0.02)

            # Ліквідації Long-позицій (під свінг-лоями)
            for low in lows:
                if low <= btc_price * 1.02:
                    liq_price = low * (1.0 - ratio)
                    if btc_price * 0.65 <= liq_price < btc_price:
                        raw_levels.append({
                            "price": liq_price,
                            "type": "long",
                            "lev": lev
                        })

            # Ліквідації Short-позицій (над свінг-хаями)
            for high in highs:
                if high >= btc_price * 0.98:
                    liq_price = high * (1.0 + ratio)
                    if btc_price < liq_price <= btc_price * 1.35:
                        raw_levels.append({
                            "price": liq_price,
                            "type": "short",
                            "lev": lev
                        })

        if not raw_levels:
            return []

        # Сортуємо та групуємо близькі рівні (кластеризація в межах 0.8%)
        raw_levels.sort(key=lambda x: x["price"])
        clustered = []
        
        for item in raw_levels:
            if not clustered:
                clustered.append([item])
            else:
                last_cluster = clustered[-1]
                avg_price = sum(x["price"] for x in last_cluster) / len(last_cluster)
                
                if abs(item["price"] - avg_price) / avg_price < 0.008 and item["type"] == last_cluster[0]["type"]:
                    last_cluster.append(item)
                else:
                    clustered.append([item])

        # Формуємо фінальний список кластерів
        final_levels = []
        for cluster in clustered:
            avg_p = sum(x["price"] for x in cluster) / len(cluster)
            c_type = cluster[0]["type"]
            max_lev = max(x["lev"] for x in cluster)
            weight = len(cluster)  # Щільність / кількість збігів

            final_levels.append({
                "price": round(avg_p, -1),
                "type": c_type,
                "lev": max_lev,
                "weight": weight
            })

        return final_levels