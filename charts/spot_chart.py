import plotly.graph_objects as go


def render_combined_cvd_chart(df_spot, df_futures):
    if df_spot.empty and df_futures.empty:
        return go.Figure()

    fig = go.Figure()

    # Лінія Спотового CVD
    if not df_spot.empty:
        fig.add_trace(
            go.Scatter(
                x=df_spot["timestamp"],
                y=df_spot["cvd_usd"] / 1e6,
                name="Spot CVD ($M)",
                mode="lines+markers",
                line=dict(color="#00E676", width=2.5),  # Якро-зелений
            )
        )

    # Лінія Ф'ючерсного CVD
    if not df_futures.empty:
        fig.add_trace(
            go.Scatter(
                x=df_futures["timestamp"],
                y=df_futures["cvd_usd"] / 1e6,
                name="Futures CVD ($M)",
                mode="lines+markers",
                line=dict(
                    color="#FF9100", width=2, dash="dash"
                ),  # Помаранчевий пунктир
            )
        )

    fig.update_layout(
        title="📊 Порівняння Спотового та Ф'ючерсного грошового потоку (CVD)",
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
        yaxis=dict(title="CVD ($M)", gridcolor="#1f293d"),
        xaxis=dict(gridcolor="#1f293d"),
    )

    return fig