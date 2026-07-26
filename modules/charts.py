import plotly.express as px
import pandas as pd


def oi_chart(df: pd.DataFrame):

    profile = (
        df.groupby("strike")["open_interest"]
        .sum()
        .reset_index()
        .sort_values("strike")
    )

    fig = px.bar(
        profile,
        x="open_interest",
        y="strike",
        orientation="h",
        title="Open Interest Profile",
        height=850
    )

    fig.update_layout(

        xaxis_title="Open Interest",

        yaxis_title="Strike",

        template="plotly_dark"

    )

    return fig