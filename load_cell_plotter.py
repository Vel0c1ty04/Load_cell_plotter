import dash 
import dash_core_components as dcc
from dash import html
from dash.dependencies import Input, Output 
import dash_bootstrap_components as dbc 
import pandas as pd 
import plotly.express as px 
import os 
import threading 
import time
import serial
import plotly.graph_objects as go

mode =  1 #select mode 1 for live data mode 0 for csv data
current_index = 0
df = pd.DataFrame(columns = ['time','load'])
csv_file2 = r"C:\Users\Vanshdeep Trivedi\OneDrive\Desktop\loadcell10.csv"
current_state = "SAFE"

# Function to read from Arduino (serial port)
def get_arduino_data():
    global csv_file2, current_state, df
    port = 'COM12'
    baud = 9600
    ser = serial.Serial(port, baud, timeout=1)

    try:
        df = pd.read_csv(csv_file2)
    except FileNotFoundError:
        print("file not found")
    print('connected to arduino at port: ', port)

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('ascii', errors='ignore').rstrip()
                #print(line)

                # Check for status updates in the line
                if "TESTBED STATE:" in line:
                    if ':' in line:
                        try:
                            current_state = line .split(":")[1].strip()
                            print(f"status: {current_state}")
                        except PermissionError:
                            current_state = line.split(":")[1].strip()
                            print(f"status: {current_state}")
                        except ValueError:
                            pass

                # Check if line contains load data in 'timestamp:load' format
                elif ':' in line and current_state == "LAUNCHED":
                    try:
                        timestamp, load = line.split(':')
                        load = float(load)
                        
                        new_data = pd.DataFrame([[timestamp, load]], columns=['time', 'load'])
                        
                        new_data.to_csv(csv_file2, mode='a', header=False, index=False)
                        
                    except PermissionError:
                        timestamp, load = line.split(':')
                        load = float(load)
                        new_data = pd.DataFrame([[timestamp,load]],columns=['time','load'])
                        
                        new_data.to_csv(csv_file2,mode='a',header=False,index=False)
                        
                    except ValueError:
                        pass
                else:
                    print(line)

    # Enter ctrl+c for closing the serial line
    except KeyboardInterrupt:
        ser.close()

# Function to read CSV data
def get_csv_data():
    global df, current_index, csv_file2, current_state
    csv_file = r"C:\Users\Vanshdeep Trivedi\OneDrive\Desktop\loadcell9.csv"
    

    if mode == 1 and current_state == "LAUNCHED":
        if os.path.exists(csv_file2):
            df = pd.read_csv(csv_file2, usecols=['time', 'load'])
            current_index = 0
            
    else:
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file, usecols=['time', 'load'])
            current_index = 0
            

# Function to plot data
def plot_data(df):
    global current_index


    if current_index < len(df):
        plotdata = df.iloc[:current_index + 1]
        current_index += 1
    else:
        plotdata = df
    

    return plotdata

# Function to generate the graph
def graph():
    global current_state
    if current_state == "LAUNCHED":
        pdata = plot_data()
        print(pdata)

        load_fig = px.line(pdata, x='time', y='load', title='', markers=True,
                       range_y=[pdata['load'].min() - 5, pdata['load'].max() + 200])
    
        load_fig.update_traces(line=dict(color='white', width=2), mode='lines+markers', marker=dict(color='white', size=2))
        load_fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False)
        )

        latest_load = f"{pdata['load'].iloc[-1]:.2f}" if len(pdata) > 0 else "N/A"
        latest_timestamp = pdata['time'].iloc[-1] if len(pdata) > 0 else "N/A"
        return load_fig, latest_load, latest_timestamp, current_state
    else:
        return go.Figure(), "N/A", "N/A", current_state

# Web app layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, '/assets/extsheet.css'])

app.layout = html.Div([
    html.H1("thrustMIT Data Plotter", className='header'),
    
    html.Div([
        html.Div([
            dcc.Graph(id='graph', config={'displayModeBar': False}, className='graph')
        ], className='graph-container'),
        
        html.Div([
            html.Div([
                html.H3('Latest values', className='panel-header'),
                html.Div([
                    html.P('Load:', className='label'),
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
        interval=300,
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
    [Input('interval-component', 'n_intervals')]
)
def update_graph(n):
    global current_state
    #if current_state != "LAUNCHED":
        #return dash.no_update
    
    fig, load, timestamp, status = graph()
    motor_details ="nah"
    
    safe_class = 'status-indicator safe'
    arm_class = 'status-indicator arm'
    launch_class = 'status-indicator launch'
    
    if status == 'SAFE':
        safe_class += ' active'
    elif status == 'ARM':
        arm_class += ' active'
    elif status == 'LAUNCH':
        launch_class += ' active'
    
    return fig, load, timestamp, motor_details, safe_class, arm_class, launch_class

# Main function to run the app
if __name__ == '__main__':
    if mode == 1:
        threading.Thread(target=get_arduino_data, daemon=True).start()
    else:
        get_csv_data()

    app.run_server(debug=True)
