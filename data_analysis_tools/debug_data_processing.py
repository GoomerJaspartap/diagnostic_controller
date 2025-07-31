#!/usr/bin/env python3
"""
Debug script to understand the data processing issue
"""

import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json

def debug_data_processing():
    """Debug the data processing to understand why only 2 data points are shown"""
    
    print("🔍 Debugging Data Processing...")
    
    # Load the data exactly like the endpoints
    filepath = "uploads/jass_test.xlsx"
    sheet_name = "1 s"
    skip_rows = []
    
    print(f"\n📊 Loading data from: {filepath}")
    print(f"   Sheet: {sheet_name}")
    print(f"   Skip rows: {skip_rows}")
    
    # Load the data
    df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows)
    print(f"   Original DataFrame shape: {df.shape}")
    
    # Drop completely empty rows
    df.dropna(how='all', inplace=True)
    print(f"   After dropping empty rows: {df.shape}")
    
    # Check the columns
    x_col = "Sample No"
    y_cols = ["Elapsed Time"]
    
    print(f"\n📋 Column Analysis:")
    print(f"   Available columns: {list(df.columns)}")
    print(f"   X column '{x_col}' exists: {x_col in df.columns}")
    print(f"   Y column '{y_cols[0]}' exists: {y_cols[0] in df.columns}")
    
    if x_col in df.columns and y_cols[0] in df.columns:
        print(f"\n📈 Data Analysis:")
        print(f"   X column data type: {df[x_col].dtype}")
        print(f"   Y column data type: {df[y_cols[0]].dtype}")
        
        # Check for NaN values
        x_nan_count = df[x_col].isna().sum()
        y_nan_count = df[y_cols[0]].isna().sum()
        print(f"   NaN values in X column: {x_nan_count}")
        print(f"   NaN values in Y column: {y_nan_count}")
        
        # Show first 10 values
        print(f"\n🔍 First 10 values:")
        print(f"   X values: {df[x_col].head(10).tolist()}")
        print(f"   Y values: {df[y_cols[0]].head(10).tolist()}")
        
        # Check if there are any non-NaN values
        x_valid = df[x_col].notna()
        y_valid = df[y_cols[0]].notna()
        both_valid = x_valid & y_valid
        
        print(f"\n✅ Valid Data Points:")
        print(f"   Valid X values: {x_valid.sum()}")
        print(f"   Valid Y values: {y_valid.sum()}")
        print(f"   Both X and Y valid: {both_valid.sum()}")
        
        if both_valid.sum() > 0:
            # Get the valid data
            valid_df = df[both_valid]
            print(f"   Valid data shape: {valid_df.shape}")
            
            # Show the valid data
            print(f"\n📊 Valid Data (first 10 rows):")
            print(f"   X values: {valid_df[x_col].head(10).tolist()}")
            print(f"   Y values: {valid_df[y_cols[0]].head(10).tolist()}")
            
            # Create the graph with valid data
            print(f"\n🎨 Creating Graph...")
            traces = []
            for y_col in y_cols:
                trace = go.Scatter(
                    x=valid_df[x_col],
                    y=valid_df[y_col],
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
            
            print(f"   Graph JSON length: {len(graph_json)}")
            
            # Parse to check data
            graph_obj = json.loads(graph_json)
            print(f"   Number of traces: {len(graph_obj['data'])}")
            if graph_obj['data']:
                trace = graph_obj['data'][0]
                print(f"   X-axis data points: {len(trace['x'])}")
                print(f"   Y-axis data points: {len(trace['y'])}")
                print(f"   First few X values: {trace['x'][:5]}")
                print(f"   First few Y values: {trace['y'][:5]}")
        else:
            print("❌ No valid data points found!")
    
    else:
        print("❌ Required columns not found!")

if __name__ == "__main__":
    debug_data_processing() 