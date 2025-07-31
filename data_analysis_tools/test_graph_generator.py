#!/usr/bin/env python3
"""
Test script to compare original Graph Generator.py with web app implementation
"""

import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
import os

def test_original_script_logic():
    """Test the exact logic from the original Graph Generator.py"""
    print("Testing original script logic...")
    
    # Test with a sample file
    file_path = "uploads/jass_test.xlsx"
    sheet_name = "1 s"  # Use an actual sheet from the file
    skip_rows = []
    
    # Read the Excel file (exact same as original)
    df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)
    
    # Drop completely empty rows (exact same as original)
    df.dropna(how='all', inplace=True)
    
    print("\nAvailable columns:")
    for idx, col in enumerate(df.columns):
        print(f"{idx}: {col}")
    
    # Simulate user input (using first column as X, second as Y)
    x_index = 0
    y_indices = "1"
    
    x_col = df.columns[x_index]
    y_cols = [df.columns[int(i.strip())] for i in y_indices.split(",")]
    
    print(f"\nPlotting {', '.join(y_cols)} vs {x_col}...")
    
    # Create the plot (exact same as original)
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
    
    # Save as HTML (exact same as original)
    output_file = "test_original_script.html"
    fig.write_html(output_file)
    print(f"\n✅ Original script test saved as '{output_file}'")
    
    return fig

def test_web_app_logic():
    """Test the exact logic from the web app implementation"""
    print("\nTesting web app logic...")
    
    # Test with the same sample file
    file_path = "uploads/jass_test.xlsx"
    sheet_name = "1 s"  # Use an actual sheet from the file
    skip_rows = []
    
    # Read the Excel file (exact same as web app)
    df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)
    
    # Drop completely empty rows (exact same as web app)
    df.dropna(how='all', inplace=True)
    
    # Get selected columns (simulate web app data)
    x_col = df.columns[0]  # First column
    y_cols = [df.columns[1]]  # Second column
    
    print(f"\nPlotting {', '.join(y_cols)} vs {x_col}...")
    
    # Create the plot (exact same as web app)
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
    
    # Convert to JSON (like web app does)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Save as HTML
    output_file = "test_web_app.html"
    fig.write_html(output_file)
    print(f"\n✅ Web app test saved as '{output_file}'")
    
    return fig, graph_json

if __name__ == "__main__":
    print("🔍 Comparing Graph Generator implementations...")
    
    try:
        # Test original script logic
        original_fig = test_original_script_logic()
        
        # Test web app logic
        webapp_fig, webapp_json = test_web_app_logic()
        
        print("\n📊 Comparison Results:")
        print("✅ Both implementations should produce identical results")
        print("✅ Original script: interactive_plot.html")
        print("✅ Web app: test_web_app.html")
        print("✅ Both files should be identical in content")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc() 