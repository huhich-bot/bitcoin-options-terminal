import pandas as pd


class MaxPainCalculator:

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def calculate(self):

        strikes = sorted(self.df["strike"].unique())

        best_strike = None
        lowest_loss = float("inf")

        results = []

        for settlement in strikes:

            total_loss = 0

            for _, row in self.df.iterrows():

                strike = row["strike"]
                oi = row["open_interest"]
                option_type = row["type"]

                if option_type == "call":
                    intrinsic = max(0, settlement - strike)
                else:
                    intrinsic = max(0, strike - settlement)

                total_loss += intrinsic * oi

            results.append({
                "strike": settlement,
                "loss": total_loss
            })

            if total_loss < lowest_loss:
                lowest_loss = total_loss
                best_strike = settlement

        return best_strike, pd.DataFrame(results)