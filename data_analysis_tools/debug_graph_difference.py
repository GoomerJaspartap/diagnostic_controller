#!/usr/bin/env python3
"""
Debug script to test both display and download endpoints with the same data
"""

import requests
import json
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import os

def test_both_endpoints():
    """Test both display and download endpoints with the same data"""
    base_url = "http://localhost:5003"
    
    print("🔍 Testing Display vs Download Endpoints...")
    
    # Test data - use the same parameters for both
    test_data = {
        "filename": "jass_test.xlsx",
        "sheet_name": "1 s",
        "skip_rows": [],
        "x_axis": "Sample No",
        "y_axes": ["Elapsed Time"]
    }
    
    print(f"\n📊 Test Data:")
    print(f"   File: {test_data['filename']}")
    print(f"   Sheet: {test_data['sheet_name']}")
    print(f"   X-axis: {test_data['x_axis']}")
    print(f"   Y-axes: {test_data['y_axes']}")
    
    # Test 1: Display endpoint
    print("\n1. Testing Display Endpoint (/create_simple_graph)...")
    response = requests.post(f"{base_url}/create_simple_graph", 
                           json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Display endpoint successful")
            display_graph = data['graph']
            print(f"   Graph JSON length: {len(display_graph)}")
            
            # Parse the JSON to see the actual data
            try:
                graph_obj = json.loads(display_graph)
                print(f"   Number of traces: {len(graph_obj['data'])}")
                if graph_obj['data']:
                    trace = graph_obj['data'][0]
                    print(f"   X-axis data points: {len(trace['x'])}")
                    print(f"   Y-axis data points: {len(trace['y'])}")
                    print(f"   First few X values: {trace['x'][:5]}")
                    print(f"   First few Y values: {trace['y'][:5]}")
            except Exception as e:
                print(f"   Error parsing display graph: {e}")
        else:
            print(f"❌ Display endpoint failed: {data.get('error')}")
            return
    else:
        print(f"❌ Display endpoint request failed: {response.status_code}")
        return
    
    # Test 2: Download endpoint
    print("\n2. Testing Download Endpoint (/download_simple_graph_html)...")
    response = requests.post(f"{base_url}/download_simple_graph_html", 
                           json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Download endpoint successful")
            download_html = data['html_content']
            print(f"   HTML length: {len(download_html)}")
            
            # Extract the graph data from HTML to compare
            try:
                # Find the plotly data in the HTML
                start_marker = 'Plotly.newPlot('
                end_marker = '));'
                
                start_idx = download_html.find(start_marker)
                if start_idx != -1:
                    # Find the data section
                    data_start = download_html.find('[{"', start_idx)
                    if data_start != -1:
                        # Find the end of the data section
                        data_end = download_html.find('}],', data_start)
                        if data_end != -1:
                            data_end += 3  # Include the '}],'
                            graph_data_section = download_html[data_start:data_end]
                            print(f"   Found graph data section: {len(graph_data_section)} chars")
                            
                            # Try to parse it as JSON
                            try:
                                # Clean up the data section to make it valid JSON
                                clean_data = graph_data_section.replace("'", '"')
                                graph_data = json.loads(clean_data)
                                print(f"   Download graph traces: {len(graph_data)}")
                                if graph_data:
                                    trace = graph_data[0]
                                    print(f"   Download X-axis data points: {len(trace['x'])}")
                                    print(f"   Download Y-axis data points: {len(trace['y'])}")
                                    print(f"   Download first few X values: {trace['x'][:5]}")
                                    print(f"   Download first few Y values: {trace['y'][:5]}")
                            except Exception as e:
                                print(f"   Error parsing download graph data: {e}")
            except Exception as e:
                print(f"   Error extracting graph data from HTML: {e}")
        else:
            print(f"❌ Download endpoint failed: {data.get('error')}")
            return
    else:
        print(f"❌ Download endpoint request failed: {response.status_code}")
        return
    
    # Test 3: Compare the actual data processing
    print("\n3. Testing Direct Data Processing...")
    try:
        filepath = "uploads/jass_test.xlsx"
        df = pd.read_excel(filepath, sheet_name="1 s", skiprows=[])
        df.dropna(how='all', inplace=True)
        
        print(f"   DataFrame shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        
        x_col = "Sample No"
        y_cols = ["Elapsed Time"]
        
        print(f"   X column exists: {x_col in df.columns}")
        print(f"   Y columns exist: {all(col in df.columns for col in y_cols)}")
        
        if x_col in df.columns and all(col in df.columns for col in y_cols):
            print(f"   X data length: {len(df[x_col])}")
            print(f"   Y data length: {len(df[y_cols[0]])}")
            print(f"   First few X values: {df[x_col].head().tolist()}")
            print(f"   First few Y values: {df[y_cols[0]].head().tolist()}")
            
            # Create the same graph as the endpoints
            traces = []
            for y_col in y_cols:
                trace = go.Scatter(
                    x=df[x_col],
                    y=df[y_col],
                    mode='lines',
                    name=str(y_col)
                )
                traces.append(trace)
            
            layout = go.Layout(
                title=f"{', '.join(y_cols)} vs {x_col}",
                xaxis=dict(title=str(x_col)),
                yaxis=dict(title="Values"),
                hovermode='closest'
            )
            
            fig = go.Figure(data=traces, layout=layout)
            graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
            print(f"   Direct processing graph JSON length: {len(graph_json)}")
            
            # Parse to check data
            graph_obj = json.loads(graph_json)
            print(f"   Direct processing traces: {len(graph_obj['data'])}")
            if graph_obj['data']:
                trace = graph_obj['data'][0]
                print(f"   Direct X-axis data points: {len(trace['x'])}")
                print(f"   Direct Y-axis data points: {len(trace['y'])}")
                print(f"   Direct first few X values: {trace['x'][:5]}")
                print(f"   Direct first few Y values: {trace['y'][:5]}")
        
    except Exception as e:
        print(f"   Error in direct processing: {e}")

if __name__ == "__main__":
    test_both_endpoints() 