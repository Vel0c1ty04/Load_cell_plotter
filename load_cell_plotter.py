import dash
import dash_core_components as dcc
from dash import html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import os
import threading
import time
import serial

mode = 0  # mode 1 for live data, mode 0 for CSV data
current_index = 0
df = pd.DataFrame(columns=['time', 'thrust'])
csv_file2 = r""
csv_file3 = r""  # New CSV for storing status
current_state = "SAFE"

# Function to read from Arduino
def get_arduino_data():
    global csv_file2, csv_file3, current_state, df
    port = 'COM10'
    baud = 9600
    ser = serial.Serial(port, baud, timeout=1)

    try:
        print('Connected to Arduino at port:', port)
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('ascii', errors='ignore').rstrip()

                if "TESTBED STATE:" in line:
                    try:
                        current_state = line.split(":")[1].strip()
                        print(f"Status: {current_state}")

                        # Write the current state to csv_file3
                        state_df = pd.DataFrame([[current_state]], columns=['status'])
                        state_df.to_csv(csv_file3, mode='a', header=True, index=False)

                    except (PermissionError, ValueError):
                        pass

                elif ':' in line and (current_state == "LAUNCHED" or current_state == "UNLATCHED"):
                    try:
                        timestamp, load = line.split(':')
                        load = float(load)
                        new_load = (load*500)/1024

                        new_data = pd.DataFrame([[timestamp, new_load]], columns=['time', 'thrust'])
                        new_data.to_csv(csv_file2, mode='a', header=False, index=False)

                    except (PermissionError, ValueError):
                        pass
                else:
                    print(line)
    except KeyboardInterrupt:
        ser.close()

# Function to read CSV data
def get_csv_data():
    global df, csv_file2

    if os.path.exists(csv_file2):
        df = pd.read_csv(csv_file2, usecols=['time', 'thrust'])

# Function to read the latest state 
def get_latest_state():
    global csv_file3

    if os.path.exists(csv_file3):
        if os.stat(csv_file3).st_size == 0:
            return "SAFE"

        state_df = pd.read_csv(csv_file3, usecols=['status'])
        if not state_df.empty:
            return state_df['status'].iloc[-1]
    
    return "SAFE"


# Function to plot data
def plot_data():
    global current_index, df

    if current_index < len(df):
        plotdata = df.iloc[:current_index + 1]
        current_index += 1
    else:
        plotdata = df

    return plotdata

# Function to generate the graph
def graph():
    global df

    pdata = plot_data()

    load_fig = px.line(pdata, x='time', y='thrust', title='Thrust VS Time Graph', markers=True,
                       range_y=[pdata['thrust'].min() - 5, pdata['thrust'].max() + 50])

    load_fig.update_traces(line=dict(color='white', width=2), mode='lines+markers', marker=dict(color='white', size=2))
    load_fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False)
    )

    latest_load = f"{pdata['thrust'].iloc[-1]:.2f}" if len(pdata) > 0 else "N/A"
    latest_timestamp = pdata['time'].iloc[-1] if len(pdata) > 0 else "N/A"

    return load_fig, latest_load, latest_timestamp

# Web app layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, '/assets/extsheet.css'])

app.layout = html.Div([
    dcc.Store(id='current-state-store', data="SAFE"),

    html.H1("thrustMIT", className='header'),

    html.Div([
        html.Div([
            dcc.Graph(id='graph', config={'displayModeBar': False}, className='graph')
        ], className='graph-container'),

        html.Div([
            html.Div([
                html.H3('Latest values', className='panel-header'),
                html.Div([
                    html.P('Thrust:', className='label'),
                    html.P(id='latest-load', className='value')
                ]),
                html.Div([
                    html.P('Timestamp:', className='label'),
                    html.P(id='latest-timestamp', className='value')
                ])
            ], className='panel'),

            html.Div([
                html.H3('Status', className='panel-header'),
                html.Div([
                    html.Div(id='safe-indicator', className='status-indicator safe'),
                    html.P('SAFE', className='status-label')
                ]),
                html.Div([
                    html.Div(id='arm-indicator', className='status-indicator arm'),
                    html.P('ARM', className='status-label')
                ]),
                html.Div([
                    html.Div(id='launch-indicator', className='status-indicator launch'),
                    html.P('LAUNCH', className='status-label')
                ]),
            ], className='panel'),
        ], className='side-panels'),
    ], className='main-content'),

    html.Div([
        html.H3('Motor Details', className='panel-header'),
        html.P(id='motor-details', className='motor-details')
    ], className='motor-panel'),

    dcc.Interval(
        id='interval-component',
        interval=200,  # Update interval
        n_intervals=0
    )
], className='container')

# Callback to update the graph and values
@app.callback(
    [Output('graph', 'figure'),
     Output('latest-load', 'children'),
     Output('latest-timestamp', 'children'),
     Output('motor-details', 'children'),
     Output('safe-indicator', 'className'),
     Output('arm-indicator', 'className'),
     Output('launch-indicator', 'className')],
    [Input('interval-component', 'n_intervals')],
    [State('current-state-store', 'data')]
)
def update_graph(n, stored_state):
    global current_state
    get_csv_data()

    
    current_state = get_latest_state()
    
    fig, load, timestamp = graph()

    motor_details = html.Div([
        html.P('J-class motor: Total Impulse: 1210 Ns'),
        html.P('Operating Time: 2.049 secs'),
        html.P('Operating at Max Pressure of 4.89 MPa'),
        html.Br(),
        html.P('M-class motor:'),
        html.P('Total Impulse: 9146 Ns'),
        html.P('Operating Time: 4.773 secs'),
        html.P('Max Pressure: 4.02 MPa')
    ])


    safe_class = 'status-indicator safe'
    arm_class = 'status-indicator arm'
    launch_class = 'status-indicator launch'

    if current_state == 'SAFE':
        safe_class += ' active'
    elif current_state == 'ARMED':
        arm_class += ' active'
    elif current_state == 'LAUNCHED':
        launch_class += ' active'

    return fig, load, timestamp, motor_details, safe_class, arm_class, launch_class


# Main function to run the app
if __name__ == '__main__':
    if mode == 1:
        threading.Thread(target=get_arduino_data, daemon=True).start()
    else:
        get_csv_data()

    app.run_server(debug=True)
