import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def render_tv_chart(df_ohlcv: pd.DataFrame, layers: dict, df_oi_profile: pd.DataFrame = None, df_gex_profile: pd.DataFrame = None, dte_info: str = "", profile_mode: str = "Net GEX"):
    fig = make_subplots(
        rows=1, cols=2, 
        column_widths=[0.80, 0.20], 
        shared_yaxes=True, 
        horizontal_spacing=0.01
    )

    # 1. График свечей BTC
    if not df_ohlcv.empty:
        fig.add_trace(go.Candlestick(
            x=df_ohlcv['time'],
            open=df_ohlcv['open'],
            high=df_ohlcv['high'],
            low=df_ohlcv['low'],
            close=df_ohlcv['close'],
            name="BTC/USD",
            increasing_line_color='#00FF00',
            decreasing_line_color='#FF5252'
        ), row=1, col=1)

    dte_suffix = f" ({dte_info})" if dte_info else ""

    # 2. Институциональные уровни
    if layers.get("show_max_pain") and layers.get("max_pain", 0) > 0:
        fig.add_hline(y=layers["max_pain"], line_dash="dot", line_color="#E040FB", line_width=2,
                      annotation_text=f"Max Pain: ${layers['max_pain']:,.0f}{dte_suffix}", 
                      annotation_position="bottom right", annotation_font_color="#E040FB", row=1, col=1)

    if layers.get("show_gamma_flip") and layers.get("gamma_flip", 0) > 0:
        fig.add_hline(y=layers["gamma_flip"], line_dash="dashdot", line_color="#FF9100", line_width=2,
                      annotation_text=f"Vol Trigger (Gamma Flip): ${layers['gamma_flip']:,.0f}", 
                      annotation_position="top left", annotation_font_color="#FF9100", row=1, col=1)

    if layers.get("show_call_wall") and layers.get("call_wall", 0) > 0:
        fig.add_hline(y=layers["call_wall"], line_dash="solid", line_color="#00E676", line_width=2,
                      annotation_text=f"Call Wall: ${layers['call_wall']:,.0f}", 
                      annotation_position="top right", annotation_font_color="#00E676", row=1, col=1)

    if layers.get("show_put_wall") and layers.get("put_wall", 0) > 0:
        fig.add_hline(y=layers["put_wall"], line_dash="solid", line_color="#FF5252", line_width=2,
                      annotation_text=f"Put Wall: ${layers['put_wall']:,.0f}", 
                      annotation_position="bottom right", annotation_font_color="#FF5252", row=1, col=1)

    # 3. Горизонтальный профиль справа (Net GEX или OI Profile)
    if profile_mode == "Net GEX" and df_gex_profile is not None and not df_gex_profile.empty:
        if not df_ohlcv.empty:
            min_p = df_ohlcv['low'].min() * 0.85
            max_p = df_ohlcv['high'].max() * 1.15
            df_prof = df_gex_profile[(df_gex_profile['strike'] >= min_p) & (df_gex_profile['strike'] <= max_p)]
        else:
            df_prof = df_gex_profile

        colors = ['#00E676' if val >= 0 else '#FF5252' for val in df_prof['net_gex']]

        fig.add_trace(go.Bar(
            y=df_prof['strike'],
            x=df_prof['net_gex'],
            orientation='h',
            name='Net GEX ($M)',
            marker_color=colors,
            hovertemplate="Страйк: $%{y:,.0f}<br>Net GEX: $%{x:,.2f}M<extra></extra>"
        ), row=1, col=2)

    elif profile_mode == "OI Profile" and df_oi_profile is not None and not df_oi_profile.empty:
        if not df_ohlcv.empty:
            min_p = df_ohlcv['low'].min() * 0.85
            max_p = df_ohlcv['high'].max() * 1.15
            df_prof = df_oi_profile[(df_oi_profile['strike'] >= min_p) & (df_oi_profile['strike'] <= max_p)]
        else:
            df_prof = df_oi_profile

        fig.add_trace(go.Bar(
            y=df_prof['strike'],
            x=df_prof['call'],
            orientation='h',
            name='Call OI',
            marker_color='rgba(0, 230, 118, 0.7)',
            hovertemplate="Страйк: $%{y:,.0f}<br>Call OI: %{x:,.1f} BTC<extra></extra>"
        ), row=1, col=2)

        fig.add_trace(go.Bar(
            y=df_prof['strike'],
            x=df_prof['put'],
            orientation='h',
            name='Put OI',
            marker_color='rgba(255, 82, 82, 0.7)',
            hovertemplate="Страйк: $%{y:,.0f}<br>Put OI: %{x:,.1f} BTC<extra></extra>"
        ), row=1, col=2)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#09140B", 
        plot_bgcolor="#09140B",
        title=f"BTC/USD и Институциональный Профиль ({profile_mode})",
        yaxis_title="Цена ($)",
        barmode='stack',
        dragmode="pan",
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(gridcolor="#132A17", showgrid=True, fixedrange=False),
        xaxis2=dict(gridcolor="#132A17", showgrid=True, title=f"{profile_mode}"),
        yaxis=dict(gridcolor="#132A17", showgrid=True, side="left", fixedrange=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def render_gex_bar_chart(df_gex_profile: pd.DataFrame):
    fig = go.Figure()
    if df_gex_profile.empty:
        return fig

    colors = ['#00E676' if val >= 0 else '#FF5252' for val in df_gex_profile['net_gex']]

    fig.add_trace(go.Bar(
        x=df_gex_profile['strike'],
        y=df_gex_profile['net_gex'],
        name='Net GEX ($M)',
        marker_color=colors
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#09140B",
        plot_bgcolor="#09140B",
        title="Профиль Gamma Exposure (Net GEX) по Страйкам ($ Миллионы)",
        xaxis_title="Страйк ($)",
        yaxis_title="Net GEX ($M)",
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig


def render_oi_bar_chart(df_oi_profile: pd.DataFrame):
    fig = go.Figure()
    if df_oi_profile.empty:
        return fig

    fig.add_trace(go.Bar(
        x=df_oi_profile['strike'],
        y=df_oi_profile['call'],
        name='Call OI',
        marker_color='#00E676'
    ))

    fig.add_trace(go.Bar(
        x=df_oi_profile['strike'],
        y=df_oi_profile['put'],
        name='Put OI',
        marker_color='#FF5252'
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#09140B",
        plot_bgcolor="#09140B",
        title="Распределение Открытого Интереса Call / Put по Страйкам",
        xaxis_title="Страйк ($)",
        yaxis_title="Открытый Интерес (BTC)",
        barmode='group',
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig


def render_history_chart(df_history: pd.DataFrame):
    fig = go.Figure()
    if df_history.empty:
        return fig

    df_sorted = df_history.sort_values("timestamp")

    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['btc_price'],
        mode='lines+markers', name='Цена BTC', line=dict(color='#00E676', width=2)
    ))

    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['max_pain'],
        mode='lines', name='Max Pain', line=dict(color='#E040FB', width=2, dash='dot')
    ))

    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['call_wall'],
        mode='lines', name='Call Wall', line=dict(color='#00B0FF', width=1, dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'], y=df_sorted['put_wall'],
        mode='lines', name='Put Wall', line=dict(color='#FF5252', width=1, dash='dash')
    ))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#09140B", plot_bgcolor="#09140B",
        title="Динамика Цены BTC и Уровней Опционов во Времени",
        yaxis_title="Цена ($)", xaxis_title="Время снимка", dragmode="pan",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig