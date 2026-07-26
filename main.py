import streamlit as st

from modules.deribit import DeribitAPI
from modules.maxpain import MaxPainCalculator
from modules.charts import oi_chart

st.set_page_config(
    page_title="Bitcoin Options Intelligence",
    page_icon="📈",
    layout="wide"
)

st.title("₿ Bitcoin Options Intelligence")

api = DeribitAPI()

with st.spinner("Loading Deribit..."):

    price = api.get_btc_price()

    df = api.load_options()

calculator = MaxPainCalculator(df)

max_pain, losses = calculator.calculate()

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "BTC",
        f"${price:,.2f}"
    )

with c2:
    st.metric(
        "Max Pain",
        f"${max_pain:,.0f}"
    )

with c3:

    st.metric(
        "Options",
        len(df)
    )

st.divider()

st.plotly_chart(
    oi_chart(df),
    use_container_width=True
)

st.divider()

st.subheader("Deribit Options")

st.dataframe(
    df,
    use_container_width=True,
    height=500
)