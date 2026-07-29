from datetime import datetime
import math
import numpy as np
import pandas as pd


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x**2)


def calculate_bs_greeks(
    S: float, K: float, T: float, r: float = 0.0, sigma: float = 0.55
) -> dict:
    """Расчет Греков (Delta, Gamma, Vanna, Charm) по Блэку-Шоулзу."""
    if T <= 0.0001 or sigma <= 0 or S <= 0 or K <= 0:
        return {
            "delta_call": 0.0,
            "delta_put": 0.0,
            "gamma": 0.0,
            "vanna": 0.0,
            "charm_call": 0.0,
            "charm_put": 0.0,
        }
    try:
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        pdf_d1 = norm_pdf(d1)
        cdf_d1 = norm_cdf(d1)
        cdf_minus_d2 = norm_cdf(-d2)

        gamma = pdf_d1 / (S * sigma * np.sqrt(T))
        vanna = -pdf_d1 * d2 / sigma

        # Charm (Delta Bleed)
        charm_call = -pdf_d1 * (
            2 * r * T - d2 * sigma * np.sqrt(T)
        ) / (2 * T * sigma * np.sqrt(T))
        charm_put = charm_call + r * math.exp(-r * T) * cdf_minus_d2

        return {
            "delta_call": float(cdf_d1),
            "delta_put": float(cdf_d1 - 1.0),
            "gamma": float(gamma),
            "vanna": float(vanna),
            "charm_call": float(charm_call),
            "charm_put": float(charm_put),
        }
    except Exception:
        return {
            "delta_call": 0.0,
            "delta_put": 0.0,
            "gamma": 0.0,
            "vanna": 0.0,
            "charm_call": 0.0,
            "charm_put": 0.0,
        }


def calculate_bs_gamma(
    S: float, K: float, T: float, r: float = 0.0, sigma: float = 0.55
) -> float:
    greeks = calculate_bs_greeks(S, K, T, r, sigma)
    return greeks["gamma"]


class OptionAnalytics:

    def __init__(self, df_options: pd.DataFrame):
        if isinstance(df_options, pd.DataFrame) and not df_options.empty:
            self.df = df_options.copy()
        else:
            self.df = pd.DataFrame(
                columns=[
                    "instrument_name",
                    "strike",
                    "type",
                    "open_interest",
                    "iv",
                    "expiration_str",
                    "expiration_date",
                    "dte",
                ]
            )

    def get_expirations(self) -> list:
        if self.df.empty or "expiration_str" not in self.df.columns:
            return []
        df_sorted = (
            self.df.sort_values("dte") if "dte" in self.df.columns else self.df
        )
        return list(
            dict.fromkeys(df_sorted["expiration_str"].dropna().tolist())
        )

    def calculate_skew_25d(self, spot_price: float = 0.0) -> float:
        """Расчет 25D Skew: IV(Put 25D) - IV(Call 25D)."""
        if self.df.empty:
            return 0.0
        try:
            df_work = self.df.copy()
            if spot_price <= 0:
                spot_price = df_work["strike"].median()

            df_work["T"] = np.maximum(df_work["dte"] / 365.0, 0.001)

            deltas = []
            for _, r in df_work.iterrows():
                greeks = calculate_bs_greeks(
                    spot_price, r["strike"], r["T"], sigma=r.get("iv", 0.55)
                )
                deltas.append(
                    greeks["delta_call"]
                    if r["type"] == "call"
                    else greeks["delta_put"]
                )

            df_work["delta"] = deltas

            calls_25d = df_work[
                (df_work["type"] == "call")
                & (df_work["delta"].between(0.15, 0.35))
            ]
            puts_25d = df_work[
                (df_work["type"] == "put")
                & (df_work["delta"].between(-0.35, -0.15))
            ]

            if calls_25d.empty or puts_25d.empty:
                calls_25d = df_work[
                    (df_work["type"] == "call")
                    & (df_work["strike"] > spot_price * 1.05)
                ]
                puts_25d = df_work[
                    (df_work["type"] == "put")
                    & (df_work["strike"] < spot_price * 0.95)
                ]

            if calls_25d.empty or puts_25d.empty:
                return 0.0

            avg_call_iv = (
                calls_25d["mark_iv"].mean()
                if "mark_iv" in calls_25d.columns
                else calls_25d["iv"].mean() * 100
            )
            avg_put_iv = (
                puts_25d["mark_iv"].mean()
                if "mark_iv" in puts_25d.columns
                else puts_25d["iv"].mean() * 100
            )

            skew = avg_put_iv - avg_call_iv
            return round(float(skew), 2)
        except Exception:
            return 0.0

    def calculate_metrics(
        self, exp_filter: str = "Все", spot_price: float = 0.0
    ) -> dict:
        if self.df.empty:
            return {
                "call_wall": 0.0,
                "put_wall": 0.0,
                "pcr": 0.0,
                "weighted_pcr": 0.0,
                "nearest_exp": "N/A",
                "nearest_dte": 0,
            }

        df_filtered = self.df.copy()
        if exp_filter != "Все" and "expiration_str" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["expiration_str"] == exp_filter
            ]

        if df_filtered.empty:
            df_filtered = self.df

        calls = df_filtered[df_filtered["type"] == "call"]
        puts = df_filtered[df_filtered["type"] == "put"]

        total_call_oi = (
            calls["open_interest"].sum() if not calls.empty else 0.0
        )
        total_put_oi = puts["open_interest"].sum() if not puts.empty else 0.0
        pcr = (
            round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0.0
        )

        df_filtered["dte_weight"] = 1.0 / np.sqrt(df_filtered["dte"] + 0.1)
        df_filtered["weighted_oi"] = (
            df_filtered["open_interest"] * df_filtered["dte_weight"]
        )

        w_calls = df_filtered[df_filtered["type"] == "call"][
            "weighted_oi"
        ].sum()
        w_puts = df_filtered[df_filtered["type"] == "put"]["weighted_oi"].sum()
        weighted_pcr = round(w_puts / w_calls, 2) if w_calls > 0 else 0.0

        call_wall = 0.0
        if not calls.empty and calls["open_interest"].sum() > 0:
            call_wall = float(
                calls.groupby("strike")["open_interest"].sum().idxmax()
            )

        put_wall = 0.0
        if not puts.empty and puts["open_interest"].sum() > 0:
            put_wall = float(
                puts.groupby("strike")["open_interest"].sum().idxmax()
            )

        nearest_exp = "N/A"
        nearest_dte = 0
        if "dte" in self.df.columns and not self.df.empty:
            min_idx = self.df["dte"].idxmin()
            min_row = self.df.loc[min_idx]
            nearest_exp = str(min_row.get("expiration_str", "N/A"))
            nearest_dte = int(min_row.get("dte", 0))

        return {
            "call_wall": call_wall,
            "put_wall": put_wall,
            "pcr": pcr,
            "weighted_pcr": weighted_pcr,
            "nearest_exp": nearest_exp,
            "nearest_dte": nearest_dte,
        }

    def calculate_max_pain(self, exp_filter: str = "Все") -> float:
        if self.df.empty:
            return 0.0

        df_filtered = self.df.copy()
        if exp_filter != "Все" and "expiration_str" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["expiration_str"] == exp_filter
            ]

        if df_filtered.empty:
            df_filtered = self.df

        strikes = np.sort(df_filtered["strike"].unique())
        if len(strikes) == 0:
            return 0.0

        calls = df_filtered[df_filtered["type"] == "call"]
        puts = df_filtered[df_filtered["type"] == "put"]

        total_losses = []
        for s in strikes:
            call_loss = (
                np.maximum(0, s - calls["strike"].values)
                * calls["open_interest"].values
                if not calls.empty
                else 0
            )
            put_loss = (
                np.maximum(0, puts["strike"].values - s)
                * puts["open_interest"].values
                if not puts.empty
                else 0
            )
            total_losses.append(np.sum(call_loss) + np.sum(put_loss))

        min_idx = np.argmin(total_losses)
        return float(strikes[min_idx])

    def get_oi_profile(self, exp_filter: str = "Все") -> pd.DataFrame:
        if self.df.empty:
            return pd.DataFrame(columns=["strike", "call", "put", "total_oi"])

        df_filtered = self.df.copy()
        if exp_filter != "Все" and "expiration_str" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["expiration_str"] == exp_filter
            ]

        if df_filtered.empty:
            return pd.DataFrame(columns=["strike", "call", "put", "total_oi"])

        profile = (
            df_filtered.groupby(["strike", "type"])["open_interest"]
            .sum()
            .unstack(fill_value=0)
        )

        if "call" not in profile.columns:
            profile["call"] = 0.0
        if "put" not in profile.columns:
            profile["put"] = 0.0

        profile["total_oi"] = profile["call"] + profile["put"]
        profile = profile.reset_index().sort_values("strike")
        return profile

    def get_gex_profile(
        self, exp_filter: str = "Все", spot_price: float = 0.0
    ) -> pd.DataFrame:
        if self.df.empty or spot_price <= 0:
            return pd.DataFrame(
                columns=["strike", "call_gex", "put_gex", "net_gex"]
            )

        df_filtered = self.df.copy()
        if exp_filter != "Все" and "expiration_str" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["expiration_str"] == exp_filter
            ]

        if df_filtered.empty:
            return pd.DataFrame(
                columns=["strike", "call_gex", "put_gex", "net_gex"]
            )

        df_filtered["T"] = np.maximum(df_filtered["dte"] / 365.0, 0.001)

        df_filtered["gamma"] = df_filtered.apply(
            lambda r: calculate_bs_gamma(
                spot_price, r["strike"], r["T"], sigma=r.get("iv", 0.55)
            ),
            axis=1,
        )

        df_filtered["gex_m"] = df_filtered.apply(
            lambda r: (
                (r["open_interest"] * r["gamma"] * (spot_price**2) * 0.01 / 1e6)
                if r["type"] == "call"
                else (
                    -r["open_interest"]
                    * r["gamma"]
                    * (spot_price**2)
                    * 0.01
                    / 1e6
                )
            ),
            axis=1,
        )

        gex_calls = (
            df_filtered[df_filtered["type"] == "call"]
            .groupby("strike")["gex_m"]
            .sum()
        )
        gex_puts = (
            df_filtered[df_filtered["type"] == "put"]
            .groupby("strike")["gex_m"]
            .sum()
        )

        profile = pd.DataFrame(
            {"call_gex": gex_calls, "put_gex": gex_puts}
        ).fillna(0.0)
        profile["net_gex"] = profile["call_gex"] + profile["put_gex"]
        profile = profile.reset_index().sort_values("strike")
        return profile

    def get_vanna_charm_profile(
        self, exp_filter: str = "Все", spot_price: float = 0.0
    ) -> pd.DataFrame:
        if self.df.empty or spot_price <= 0:
            return pd.DataFrame(
                columns=["strike", "vanna_m", "charm_m", "net_vanna_charm"]
            )

        df_work = self.df.copy()
        if exp_filter != "Все" and "expiration_str" in df_work.columns:
            df_work = df_work[df_work["expiration_str"] == exp_filter]

        if df_work.empty:
            return pd.DataFrame(
                columns=["strike", "vanna_m", "charm_m", "net_vanna_charm"]
            )

        df_work["T"] = np.maximum(df_work["dte"] / 365.0, 0.001)

        vanna_list, charm_list = [], []
        for _, r in df_work.iterrows():
            g = calculate_bs_greeks(
                spot_price, r["strike"], r["T"], sigma=r.get("iv", 0.55)
            )
            oi = r["open_interest"]

            # Vanna Exposure ($M на 1% IV)
            v_val = oi * g["vanna"] * spot_price * 0.01 / 1e6
            vanna_list.append(v_val if r["type"] == "call" else -v_val)

            # Charm Exposure ($M в день)
            ch_val = (
                oi
                * (
                    g["charm_call"]
                    if r["type"] == "call"
                    else g["charm_put"]
                )
                * spot_price
                / 365.0
                / 1e6
            )
            charm_list.append(ch_val)

        df_work["vanna_m"] = vanna_list
        df_work["charm_m"] = charm_list

        profile = (
            df_work.groupby("strike")[["vanna_m", "charm_m"]]
            .sum()
            .reset_index()
        )
        profile["net_vanna_charm"] = profile["vanna_m"] + profile["charm_m"]
        return profile.sort_values("strike")

    def calculate_net_gex(
        self, exp_filter: str = "Все", spot_price: float = 0.0
    ) -> float:
        gex_df = self.get_gex_profile(
            exp_filter=exp_filter, spot_price=spot_price
        )
        if gex_df.empty:
            return 0.0
        return float(gex_df["net_gex"].sum())

    def calculate_vanna_charm_exposure(
        self, exp_filter: str = "Все", spot_price: float = 0.0
    ) -> tuple:
        """Возвращает суммарное Vanna ($M / 1% IV) и Charm ($M / день)."""
        v_df = self.get_vanna_charm_profile(
            exp_filter=exp_filter, spot_price=spot_price
        )
        if v_df.empty:
            return 0.0, 0.0
        return round(float(v_df["vanna_m"].sum()), 2), round(
            float(v_df["charm_m"].sum()), 2
        )

    def calculate_net_vanna(
        self, exp_filter: str = "Все", spot_price: float = 0.0
    ) -> float:
        v_df = self.get_vanna_charm_profile(
            exp_filter=exp_filter, spot_price=spot_price
        )
        if v_df.empty:
            return 0.0
        return float(v_df["vanna_m"].sum())

    def find_gamma_flip(
        self, exp_filter: str = "Все", spot_price: float = 0.0
    ) -> float:
        if self.df.empty or spot_price <= 0:
            return 0.0

        df_filtered = self.df.copy()
        if exp_filter != "Все" and "expiration_str" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["expiration_str"] == exp_filter
            ]

        if df_filtered.empty:
            df_filtered = self.df

        test_prices = np.linspace(spot_price * 0.7, spot_price * 1.3, 80)
        net_gex_curve = []

        for p in test_prices:
            total_gex = 0.0
            for _, r in df_filtered.iterrows():
                T = max(r["dte"] / 365.0, 0.001)
                gamma = calculate_bs_gamma(
                    p, r["strike"], T, sigma=r.get("iv", 0.55)
                )
                oi = r["open_interest"]
                if r["type"] == "call":
                    total_gex += oi * gamma * (p**2) * 0.01
                else:
                    total_gex -= oi * gamma * (p**2) * 0.01
            net_gex_curve.append((p, total_gex))

        for i in range(len(net_gex_curve) - 1):
            p1, g1 = net_gex_curve[i]
            p2, g2 = net_gex_curve[i + 1]
            if (g1 <= 0 and g2 >= 0) or (g1 >= 0 and g2 <= 0):
                flip_price = (
                    p1 + (0 - g1) * (p2 - p1) / (g2 - g1) if g2 != g1 else p1
                )
                return float(flip_price)

        return 0.0

    def evaluate_sentiment(
        self,
        btc_price: float,
        metrics: dict,
        max_pain: float,
        net_gex: float = 0.0,
        gamma_flip: float = 0.0,
        skew_25d: float = 0.0,
        net_vanna: float = 0.0,
    ) -> dict:
        reasons = []
        score = 0

        # 1. Gamma Режим
        if net_gex > 0.5:
            reasons.append(
                f"<b>Long Gamma (+${net_gex:,.1f}M):</b> Маркетмейкеры гасят"
                " волатильность. Рынок склонен к флэту и возврату к среднему."
            )
            score += 1
        elif net_gex < -0.5:
            reasons.append(
                f"<b>Short Gamma (-${abs(net_gex):,.1f}M):</b> Маркетмейкеры"
                " ускоряют движение. Высокий риск каскадного пробоя."
            )
            score -= 1

        # 2. Vanna Exposure
        if net_vanna != 0:
            action = "покупать" if net_vanna > 0 else "продавать"
            reasons.append(
                f"<b>Net Vanna Exposure (${net_vanna:,.1f}M / 1% IV):</b> При"
                f" скачке волатильности ММ вынуждены {action} фьючерсы."
            )

        # 3. 25D Skew
        if skew_25d > 2.0:
            reasons.append(
                f"<b>25D Skew (+{skew_25d}%):</b> Повышенный страх — киты массово"
                " скупают Put-страховку."
            )
            score -= 1
        elif skew_25d < -2.0:
            reasons.append(
                f"<b>25D Skew ({skew_25d}%):</b> Бычий перекос — высокий спрос на Call-опционы."
            )
            score += 1

        # 4. Vol Trigger
        if gamma_flip > 0:
            if btc_price > gamma_flip:
                reasons.append(
                    f"Цена (${btc_price:,.0f}) выше <b>Vol Trigger"
                    f" (${gamma_flip:,.0f})</b> — зона низкого импульсного"
                    " риска."
                )
                score += 1
            else:
                reasons.append(
                    f"Цена (${btc_price:,.0f}) ниже <b>Vol Trigger"
                    f" (${gamma_flip:,.0f})</b> — триггер ускорения падения."
                )
                score -= 1

        # 5. Max Pain
        if max_pain > 0:
            if btc_price < max_pain:
                score += 1
                reasons.append(
                    f"Цена (${btc_price:,.0f}) ниже Max Pain (${max_pain:,.0f})"
                    " — магнетический вектор вверх к экспирации."
                )
            elif btc_price > max_pain:
                score -= 1
                reasons.append(
                    f"Цена (${btc_price:,.0f}) выше Max Pain (${max_pain:,.0f})"
                    " — сдерживающий фактор сверху."
                )

        if not reasons:
            reasons.append(
                "Недостаточно данных для формирования однозначного прогноза."
            )

        if score >= 2:
            status, color = "Бычий режим (Bullish / Low Volatility)", "#00E676"
        elif score <= -2:
            status, color = (
                "Медвежий / Высокая Волатильность (Bearish Breakout)",
                "#FF5252",
            )
        else:
            status, color = "Нейтральный Флэт (Range Bound)", "#FFD600"

        return {"status": status, "color": color, "reasons": reasons}