import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

def plot_indicators(data, indicators):
    rows = 1 + indicators['MACD'] + indicators['SO'] + indicators['Volume']
    row_heights = [0.5] + [0.2] * (rows - 1) if rows > 1 else [1.0]

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=row_heights
    )

    # Grafik harga candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Candlestick'
    ), row=1, col=1)

    if indicators['MA']:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA20'], name='MA20', line=dict(color='blue', dash='dash')
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=data.index, y=data['MA50'], name='MA50', line=dict(color='red', dash='dash')
        ), row=1, col=1)

    if indicators['Ichimoku']:
        fig.add_trace(go.Scatter(x=data.index, y=data['Tenkan_sen'], name='Tenkan Sen', line=dict(color='blue')), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Kijun_sen'], name='Kijun Sen', line=dict(color='red')), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Senkou_span_A'], name='Senkou Span A', line=dict(color='green', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Senkou_span_B'], name='Senkou Span B', line=dict(color='orange', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=pd.concat([pd.Series(data.index), pd.Series(data.index[::-1])]),
            y=pd.concat([data['Senkou_span_A'], data['Senkou_span_B'][::-1]]),
            fill='toself', fillcolor='rgba(160, 160, 160, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip", showlegend=True, name='Kumo Cloud'
        ), row=1, col=1)

    current_row = 2
    if indicators['MACD']:
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD'], name='MACD', line=dict(color='blue')), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MACD_signal'], name='MACD Signal', line=dict(color='red')), row=current_row, col=1)
        fig.add_trace(go.Bar(x=data.index, y=data['MACD_hist'], name='MACD Histogram', marker_color='gray'), row=current_row, col=1)
        current_row += 1

    if indicators['SO']:
        fig.add_trace(go.Scatter(x=data.index, y=data['SlowK'], name='SlowK', line=dict(color='blue')), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['SlowD'], name='SlowD', line=dict(color='red')), row=current_row, col=1)
        current_row += 1

    if indicators['Volume']:
        fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume', marker_color='green'), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['Volume_MA20'], name='Volume MA20', line=dict(color='orange', dash='dash')), row=current_row, col=1)

    fig.update_layout(
        height=300 * rows,
        hovermode='x unified',
        margin=dict(l=20, r=20, t=40, b=40),
        legend=dict(orientation='v', yanchor='top', y=1, xanchor='left', x=1.02)
    )

    st.plotly_chart(fig, use_container_width=True)

def plot_signal_markers(df, signal_column='Final_Signal'):
    st.subheader("Grafik Sinyal")

    signal_styles = {
        'Buy': {'color': 'green', 'symbol': 'triangle-up'},
        'Sell': {'color': 'red', 'symbol': 'triangle-down'},
        'Hold': {'color': 'blue', 'symbol': 'circle'}
    }

    fig = go.Figure()

    # Tambahkan garis harga sebagai referensi
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Close'],
        mode='lines',
        name='Harga Close',
        line=dict(color='lightgray', width=1),
        showlegend=True
    ))

    for signal, style in signal_styles.items():
        df_signal = df[df[signal_column] == signal]
        if not df_signal.empty:
            fig.add_trace(go.Scatter(
                x=df_signal.index,
                y=df_signal['Close'],
                mode='markers',
                marker=dict(
                    color=style['color'],
                    size=10,
                    symbol=style['symbol']
                ),
                name=f"Sinyal {signal}"
            ))

    fig.update_layout(
        height=500,
        # title="Visualisasi Sinyal Analisis",
        xaxis_title='Tanggal',
        yaxis_title='Harga Close',
        hovermode='x unified',
        margin=dict(l=20, r=20, t=40, b=40),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)
