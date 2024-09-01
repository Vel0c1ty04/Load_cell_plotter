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
csv_file2 = r'empty_csv_file'

#read from arduino (close serial monitor)
def get_arduino_data():
    global csv_file2
    port = 'COM9'
    baud = 9600
    ser = serial.Serial(port, baud, timeout=1)

    try:
        df=pd.read_csv(csv_file2)
    except FileNotFoundError:
        print("file not found")
    print('connected to arduino at port: ',port)
    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('ascii',errors='ignore').rstrip()
                try:
                    load = float(line)
                    current_time = time.strftime('%H:%M:%S')
                    new_data = pd.DataFrame([[current_time, load]],columns=['time','load'])

                    new_data.to_csv(csv_file2, mode='a',header=False, index=False)

                    print(f"time: {current_time}, load: {load}")

                except ValueError:
                    pass
    #enter ctrl+c for closing serial line
    except KeyboardInterrupt:
        ser.close()

#gets data for plotting 
def get_csv_data():
    global df, current_index, csv_file2
    csv_file = r"file_with_data"

    if mode == 1:
        if os.path.exists(csv_file2):
            df = pd.read_csv(csv_file2, usecols=['time','load'])
            current_index = 0

    else:
        if os.path.exists(csv_file):
            df=pd.read_csv(csv_file, usecols=['time','load'])
            current_index = 0

#reads the data from the csv
def plot_data():
    global df, current_index, mode, csv_file2

    if mode==1:
        df=pd.read_csv(csv_file2, usecols=['time','load'])

    if current_index < len(df):
        plotdata = df.iloc[:current_index+1]
        current_index +=1
    else:
        plotdata = df

    return plotdata

#graph settings   
def graph():
    pdata = plot_data()

    load_fig = px.line(pdata, x='time',y='load', title='load vs time', markers=True
                           , range_y=[pdata['load'].min()-5, pdata['load'].max()+200])
    
    load_fig.update_traces(line = dict(color='blue',width=2), mode='lines+markers', marker=dict(color='blue', size=2))

    latest_val =[
        html.Div(f"load: {pdata['load'].iloc[-1]:.2f}")
    ]

    return load_fig, latest_val

#webapp settings
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

app.layout= html.Div([
    html.H1("Sensor data", style={'textAlign':'center'}),

    html.H3('latest values',style={'textAlign':'center'}),

    html.Div(id='latest-values', style={'textAlign':'center','margin':'20px'}),

    dcc.Graph(id='load-graph',animate=False,style={'height':'400px','width':'100%',}),

    dcc.Interval(
        id='interval-component',
        interval=100,#reduce the interval value for faster updates 
        n_intervals=0
    )
])

@app.callback(
    [Output('load-graph','figure'),
     Output('latest-values','children')],
     [Input('interval-component','n_intervals')]
)

def update_graph(n):
    return graph()

if __name__=='__main__':
    if mode == 1:
        threading.Thread(target=get_arduino_data, daemon=True).start()
        
    else:
        get_csv_data()

    app.run_server(debug=True)