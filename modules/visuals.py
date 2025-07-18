import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_indicators(data, indicators):
    rows = 1
    row_heights = [0.6]
    indicator_rows = [key for key in ['MACD', 'SO', 'Volume'] if indicators.get(key)]
    rows += len(indicator_rows)
    row_heights += [0.2] * len(indicator_rows)

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights
    )

    # Candlestick dan indikator utama
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        name='Candlestick'), row=1, col=1)

    if indicators.get('MA'):
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MA5'],
            name='MA5',
            line=dict(color='#1f77b4', dash='dash')
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MA10'],
            name='MA10',
            line=dict(color='#ff7f0e', dash='dash')
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MA20'],
            name='MA20',
            line=dict(color="#c906fa", dash='dash')
        ), row=1, col=1)

    if indicators.get('Ichimoku'):
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Tenkan_sen'],
            name='Tenkan Sen',
            line=dict(color="#2A7201")
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Kijun_sen'],
            name='Kijun Sen',
            line=dict(color="#812704")
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Senkou_span_A'],
            name='Senkou Span A',
            line=dict(color="#00ff00", dash='dash')
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Senkou_span_B'],
            name='Senkou Span B',
            line=dict(color="#ff0000", dash='dash')
        ), row=1, col=1)
        trend_up = data['Senkou_span_A'] >= data['Senkou_span_B']
        segments = []

        if len(trend_up) > 1:
            start = 0
            for i in range(1, len(trend_up)):
                try:
                    if trend_up.iloc[i] != trend_up.iloc[start]:
                        segments.append((start, i - 1, trend_up.iloc[start]))
                        start = i
                except IndexError:
                    continue
            if start < len(trend_up):
                try:
                    segments.append((start, len(data) - 1, trend_up.iloc[start]))
                except IndexError:
                    pass

        shown_up, shown_down = False, False
        for seg_start, seg_end, is_up in segments:
            x_seg = pd.concat([
                pd.Series(data.index[seg_start:seg_end + 1]),
                pd.Series(data.index[seg_end:seg_start - 1 if seg_start > 0 else None:-1])
            ])
            y_seg = pd.concat([
                data['Senkou_span_A'].iloc[seg_start:seg_end + 1],
                data['Senkou_span_B'].iloc[seg_start:seg_end + 1][::-1]
            ])
            fig.add_trace(go.Scatter(
                x=x_seg,
                y=y_seg,
                fill='toself',
                fillcolor='rgba(0,255,0,0.2)' if is_up else 'rgba(255,0,0,0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                hoverinfo="skip",
                showlegend=(not shown_up if is_up else not shown_down),
                name='Kumo Uptrend' if is_up else 'Kumo Downtrend'
            ), row=1, col=1)
            if is_up:
                shown_up = True
            else:
                shown_down = True


    current_row = 2
    for ind in indicator_rows:
        if ind == 'MACD':
            macd_colors = ['green' if h >= 0 else 'red' for h in data['MACD_hist']]
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MACD'],
                name='MACD',
                line=dict(color='#1f77b4')
            ), row=current_row, col=1)
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MACD_signal'],
                name='MACD Signal',
                line=dict(color='#d62728')
            ), row=current_row, col=1)
            fig.add_trace(go.Bar(x=data.index, y=data['MACD_hist'], name='MACD Histogram', marker_color=macd_colors), row=current_row, col=1)
        elif ind == 'SO':
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['SlowK'],
                name='SlowK',
                line=dict(color='#2ca02c')
            ), row=current_row, col=1)
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['SlowD'],
                name='SlowD',
                line=dict(color='#e377c2')
            ), row=current_row, col=1)
        elif ind == 'Volume':
            fig.add_trace(go.Bar(
                x=data.index,
                y=data['Volume'],
                name='Volume',
                marker_color='#7f7f7f'
            ), row=current_row, col=1)
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['Volume_MA20'],
                name='Volume MA20',
                line=dict(color='#ff7f0e', dash='dash')
            ), row=current_row, col=1)
        current_row += 1

    fig.update_layout(
        height=300 * rows,
        hovermode='x unified',
        margin=dict(l=20, r=20, t=40, b=40),
        legend=dict(orientation='v', yanchor='top', y=1, xanchor='left', x=1.02),
        xaxis=dict(rangeslider=dict(visible=False))
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
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Close'],
        mode='lines',
        name='Harga Close',
        line=dict(color='lightgray', width=1),
        showlegend=True))

    for signal, style in signal_styles.items():
        df_signal = df[df[signal_column] == signal]
        if not df_signal.empty:
            fig.add_trace(go.Scatter(
                x=df_signal.index,
                y=df_signal['Close'],
                mode='markers',
                marker=dict(color=style['color'], size=10, symbol=style['symbol']),
                name=f"Sinyal {signal}"))

    fig.update_layout(
        height=500,
        xaxis_title='Tanggal',
        yaxis_title='Harga Close',
        hovermode='x unified',
        margin=dict(l=20, r=20, t=40, b=40),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)

def plot_signal_pairs(df, signal_pairs, show_lines=True):
    """Plot buy/sell signal pairs using candlesticks and optional connectors."""
    st.subheader("Visualisasi Pasangan Sinyal")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Candlestick'), row=1, col=1)

    for i, row in signal_pairs.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['Buy Date']], y=[row['Buy Price']], mode='markers',
            marker=dict(symbol='triangle-up', color='green', size=10),
            name=f"Buy {i+1}", showlegend=(i == 0)))

        fig.add_trace(go.Scatter(
            x=[row['Sell Date']], y=[row['Sell Price']], mode='markers',
            marker=dict(symbol='triangle-down', color='red', size=10),
            name=f"Sell {i+1}", showlegend=(i == 0)))

        if show_lines:
            fig.add_trace(go.Scatter(
                x=[row['Buy Date'], row['Sell Date']],
                y=[row['Buy Price'], row['Sell Price']],
                mode='lines',
                line=dict(dash='dot', color='blue'),
                showlegend=False
            ))

    if 'Volume' in df.columns:
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Volume'],
                name='Volume',
                marker_color='gray'
            ), row=2, col=1
        )
        if 'Volume_MA20' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Volume_MA20'],
                    name='Volume MA20',
                    line=dict(color='orange', dash='dash')
                ), row=2, col=1
            )

    fig.update_layout(
        height=600,
        hovermode='x unified',
        margin=dict(l=20, r=20, t=40, b=40),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        xaxis=dict(rangeslider=dict(visible=False))
    )
    fig.update_yaxes(title_text='Harga', row=1, col=1)
    if 'Volume' in df.columns:
        fig.update_yaxes(title_text='Volume', row=2, col=1)
    fig.update_xaxes(title_text='Tanggal', row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)