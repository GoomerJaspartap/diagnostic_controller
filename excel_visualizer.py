#!/usr/bin/env python3
"""
Excel Data Visualizer - Standalone Web Application
A Flask web app for visualizing Excel data with threshold-based color coding
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.utils
import json
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory
import numpy as np
from werkzeug.utils import secure_filename
import tempfile
import shutil

app = Flask(__name__)
app.secret_key = 'excel_visualizer_secret_key_2024'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def detect_and_convert_numeric_columns(df):
    """Detect and convert numeric columns that might be stored as strings"""
    numeric_columns = []
    
    for col in df.columns:
        # Skip if already numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_columns.append(col)
            continue
        
        # Try to convert to numeric
        try:
            # Remove common non-numeric characters
            cleaned = df[col].astype(str).str.replace(',', '').str.replace('$', '').str.replace('%', '')
            # Try to convert to numeric
            converted = pd.to_numeric(cleaned, errors='coerce')
            
            # If we have valid numeric values, use this column
            if converted.notna().sum() > 0:
                df[col] = converted
                numeric_columns.append(col)
        except:
            continue
    
    return numeric_columns

def clean_dataframe(df, datetime_columns, numeric_columns):
    """Clean dataframe by removing rows with invalid data"""
    df_clean = df.copy()
    
    # Remove rows with NaT values in datetime columns
    for col in datetime_columns:
        df_clean = df_clean.dropna(subset=[col])
    
    # Remove rows with NaN values in numeric columns
    for col in numeric_columns:
        df_clean = df_clean.dropna(subset=[col])
    
    # Remove rows where datetime values are invalid (NaT)
    for col in datetime_columns:
        # Filter out NaT values
        df_clean = df_clean[df_clean[col].notna()]
    
    return df_clean

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_datetime_column(df, column_name):
    """Parse datetime column with multiple format attempts"""
    if column_name not in df.columns:
        return None
    
    # First, let's see what type of data we're dealing with
    sample_values = df[column_name].dropna().head(5)
    if len(sample_values) == 0:
        return None
    
    # Convert to string first to handle mixed types
    df[column_name] = df[column_name].astype(str)
    
    # Try different datetime parsing strategies
    formats_to_try = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
        '%m/%d/%Y',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%d/%m/%Y',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y/%m/%d',
        '%m-%d-%Y %H:%M:%S',
        '%m-%d-%Y %H:%M',
        '%m-%d-%Y',
        '%d-%m-%Y %H:%M:%S',
        '%d-%m-%Y %H:%M',
        '%d-%m-%Y'
    ]
    
    for fmt in formats_to_try:
        try:
            # Try parsing with the specific format
            parsed = pd.to_datetime(df[column_name], format=fmt, errors='coerce')
            # Check if we have valid datetime values
            if parsed.notna().sum() > 0:
                df[column_name] = parsed
                return column_name
        except:
            continue
    
    # Try pandas automatic parsing with better error handling
    try:
        # Suppress warnings for datetime parsing
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Try to infer the format from sample values
            sample_str = sample_values.astype(str).iloc[0] if len(sample_values) > 0 else ""
            
            # Try different parsing strategies
            parsed = pd.to_datetime(df[column_name], errors='coerce')
            if parsed.notna().sum() > 0:
                df[column_name] = parsed
                return column_name
                
            # Try with dayfirst=True (for European dates)
            parsed = pd.to_datetime(df[column_name], dayfirst=True, errors='coerce')
            if parsed.notna().sum() > 0:
                df[column_name] = parsed
                return column_name
                
            # Try with yearfirst=True
            parsed = pd.to_datetime(df[column_name], yearfirst=True, errors='coerce')
            if parsed.notna().sum() > 0:
                df[column_name] = parsed
                return column_name
            
    except Exception as e:
        print(f"Error parsing datetime column {column_name}: {e}")
    
    return None

def is_value_within_bounds_realtime(start_time, time_to_achieve, current_time,
                                    threshold, start_value, target_value, current_value, steady_state_threshold=None):
    """
    Checks if current_value at current_time is within threshold of expected value on linear ramp.
    Works for both positive and negative slopes.
    """
    # Convert datetime objects to seconds for calculation
    start_time_seconds = start_time.timestamp()
    current_time_seconds = current_time.timestamp()
    
    # Calculate slope and intercept
    m = (target_value - start_value) / time_to_achieve
    b = start_value - m * start_time_seconds
    
    # Calculate expected value
    if current_time_seconds < start_time_seconds:
        expected_value = start_value
    elif current_time_seconds >= start_time_seconds + time_to_achieve:
        expected_value = target_value
    else:
        expected_value = m * current_time_seconds + b
    
    # Clamp expected value to bounds (works for both positive and negative slope)
    min_bound = min(start_value, target_value)
    max_bound = max(start_value, target_value)
    expected_value = max(min(expected_value, max_bound), min_bound)
    
    # Check if current value is within bounds
    deviation = abs(current_value - expected_value)
    if steady_state_threshold is not None and current_time_seconds >= start_time_seconds + time_to_achieve:
        in_bounds = deviation <= steady_state_threshold
    else:
        in_bounds = deviation <= threshold
    
    return in_bounds, expected_value

def create_graph_data(df, x_col, y_col, start_time, end_time, start_value, end_value, 
                     threshold, steady_state_threshold, time_to_achieve, data_start_time=None, data_end_time=None):
    """Create graph data with color coding based on threshold logic"""
    
    # Filter data and remove NaT values
    df_filtered = df.dropna(subset=[x_col, y_col]).copy()
    
    if df_filtered.empty:
        return None
    
    # Apply optional data filter if specified
    if data_start_time is not None:
        df_filtered = df_filtered[df_filtered[x_col] >= data_start_time]
    if data_end_time is not None:
        df_filtered = df_filtered[df_filtered[x_col] <= data_end_time]
    
    if df_filtered.empty:
        return None
    
    # Calculate expected curve
    time_points = []
    expected_values = []
    upper_threshold = []
    lower_threshold = []
    
    # Generate time points for the expected curve range
    curve_start_time = start_time
    curve_end_time = start_time + timedelta(seconds=time_to_achieve)
    
    # Use the data range for visualization, but ensure it covers the expected curve
    data_min_time = df_filtered[x_col].min()
    data_max_time = df_filtered[x_col].max()
    
    # Ensure we cover the full expected curve range
    min_time = min(data_min_time, curve_start_time)
    max_time = max(data_max_time, curve_end_time)
    
    print(f"Debug: Data range: {data_min_time} to {data_max_time}")
    print(f"Debug: Curve range: {curve_start_time} to {curve_end_time}")
    print(f"Debug: Final range: {min_time} to {max_time}")
    
    # Extend range slightly for better visualization
    time_range = (max_time - min_time).total_seconds()
    time_step = max(1, time_range / 200)  # 200 points for smoother curve
    print(f"Debug: Time range: {time_range:.2f} seconds, Time step: {time_step:.2f} seconds")
    
    # Add debugging for curve generation
    print(f"Debug: Data time range: {min_time} to {max_time}")
    print(f"Debug: Expected curve start time: {start_time}")
    print(f"Debug: Expected curve end time: {start_time + timedelta(seconds=time_to_achieve)}")
    print(f"Debug: Start value: {start_value}, End value: {end_value}")
    print(f"Debug: Time to achieve: {time_to_achieve}")
    
    current_time = min_time
    while current_time <= max_time:
        time_points.append(current_time)
        
        # Calculate expected value using the same logic as the dashboard
        try:
            current_time_seconds = current_time.timestamp()
            start_time_seconds = start_time.timestamp()
            
            if current_time_seconds < start_time_seconds:
                expected_value = start_value
                phase = "before"
            elif current_time_seconds >= start_time_seconds + time_to_achieve:
                expected_value = end_value
                phase = "after"
            else:
                # Linear interpolation
                m = (end_value - start_value) / time_to_achieve
                b = start_value - m * start_time_seconds
                expected_value = m * current_time_seconds + b
                phase = "during"
            
            # Debug first few curve points
            if len(expected_values) < 5:
                print(f"Debug: Curve point {len(expected_values)+1} - Time: {current_time}, Phase: {phase}, Expected: {expected_value:.2f}")
            
            # Clamp to bounds
            min_bound = min(start_value, end_value)
            max_bound = max(start_value, end_value)
            expected_value = max(min(expected_value, max_bound), min_bound)
            
            expected_values.append(expected_value)
            
            # Calculate thresholds
            if steady_state_threshold is not None and current_time_seconds >= start_time_seconds + time_to_achieve:
                upper = end_value + steady_state_threshold
                lower = end_value - steady_state_threshold
            else:
                upper = expected_value + threshold
                lower = expected_value - threshold
            
            upper_threshold.append(upper)
            lower_threshold.append(lower)
            
        except (ValueError, AttributeError, OSError):
            # Skip invalid datetime values
            continue
        
        current_time += timedelta(seconds=time_step)
    
    print(f"Debug: Generated {len(expected_values)} expected curve points")
    print(f"Debug: Expected value range: {min(expected_values)} to {max(expected_values)}")
    
    # Add more detailed debugging for the curve calculation
    if len(expected_values) > 0:
        print(f"Debug: First few expected values: {expected_values[:5]}")
        print(f"Debug: Last few expected values: {expected_values[-5:]}")
        print(f"Debug: Curve slope calculation: m = ({end_value} - {start_value}) / {time_to_achieve} = {(end_value - start_value) / time_to_achieve}")
        
        # Show a few sample calculations
        sample_times = time_points[:3] + time_points[-3:] if len(time_points) > 6 else time_points
        for i, t in enumerate(sample_times):
            t_seconds = t.timestamp()
            start_t_seconds = start_time.timestamp()
            if t_seconds < start_t_seconds:
                phase = "before"
            elif t_seconds >= start_t_seconds + time_to_achieve:
                phase = "after"
            else:
                phase = "during"
            print(f"Debug: Sample {i+1} - Time: {t}, Phase: {phase}, Expected: {expected_values[i]}")
    
    # Process actual data points
    actual_times = []
    actual_values = []
    actual_colors = []
    actual_tooltips = []
    
    for _, row in df_filtered.iterrows():
        # Skip rows with invalid datetime or NaN values
        if pd.isna(row[x_col]) or pd.isna(row[y_col]):
            continue
            
        actual_times.append(row[x_col])
        actual_values.append(row[y_col])
        
        # Determine if point is within bounds using the same logic as threshold curves
        try:
            # Convert to datetime if it's a timestamp
            if hasattr(row[x_col], 'timestamp'):
                current_time = row[x_col]
            else:
                current_time = pd.to_datetime(row[x_col])
            
            # Use datetime objects directly for comparison
            # Convert to naive datetime if needed
            if hasattr(current_time, 'to_pydatetime'):
                current_time = current_time.to_pydatetime()
            if hasattr(start_time, 'to_pydatetime'):
                start_time_normalized = start_time.to_pydatetime()
            else:
                start_time_normalized = start_time
            
            # Calculate seconds since epoch for comparison
            epoch = datetime(1970, 1, 1)
            current_time_seconds = (current_time - epoch).total_seconds()
            start_time_seconds = (start_time_normalized - epoch).total_seconds()
            
            # Debug timestamp comparison
            if len(actual_colors) < 5:
                print(f"Debug: Timestamp comparison for point {len(actual_colors)+1}:")
                print(f"  Current time: {current_time} ({current_time_seconds})")
                print(f"  Start time: {start_time} ({start_time_seconds})")
                print(f"  Difference: {current_time_seconds - start_time_seconds} seconds")
                print(f"  Time to achieve: {time_to_achieve} seconds")
                print(f"  Should be during curve: {start_time_seconds <= current_time_seconds <= start_time_seconds + time_to_achieve}")
                print("---")
            
            # Use the exact same calculation as the curve
            if current_time_seconds < start_time_seconds:
                expected_value = start_value
                phase = "before"
            elif current_time_seconds >= start_time_seconds + time_to_achieve:
                expected_value = end_value
                phase = "after"
            else:
                # Linear interpolation - same as curve calculation
                m = (end_value - start_value) / time_to_achieve
                b = start_value - m * start_time_seconds
                expected_value = m * current_time_seconds + b
                phase = "during"
            
            # Debug the calculation for first few points
            if len(actual_colors) < 5:
                print(f"Debug: Point {len(actual_colors)+1} calculation:")
                print(f"  Time: {current_time} (seconds: {current_time_seconds})")
                print(f"  Start time: {start_time} (seconds: {start_time_seconds})")
                print(f"  Phase: {phase}")
                print(f"  Start value: {start_value}, End value: {end_value}")
                print(f"  Time to achieve: {time_to_achieve}")
                if phase == "during":
                    print(f"  Slope (m): {m}, Intercept (b): {b}")
                print(f"  Expected value: {expected_value}")
                print(f"  Actual value: {row[y_col]}")
                print(f"  Difference: {abs(row[y_col] - expected_value)}")
                print("---")
            
            # Clamp expected value - same as curve calculation
            min_bound = min(start_value, end_value)
            max_bound = max(start_value, end_value)
            expected_value = max(min(expected_value, max_bound), min_bound)
            
            # Debug the calculation for first few points
            if len(actual_colors) < 5:
                print(f"Debug: Point {len(actual_colors)+1} calculation:")
                print(f"  Time: {row[x_col]} (seconds: {current_time_seconds})")
                print(f"  Start time: {start_time} (seconds: {start_time_seconds})")
                print(f"  Phase: {phase}")
                print(f"  Start value: {start_value}, End value: {end_value}")
                print(f"  Time to achieve: {time_to_achieve}")
                if phase == "during":
                    print(f"  Slope (m): {m}, Intercept (b): {b}")
                print(f"  Expected value: {expected_value}")
                print(f"  Actual value: {row[y_col]}")
                print(f"  Difference: {abs(row[y_col] - expected_value)}")
                print("---")
            
            # Use the same logic as the diagnostic controller
            actual_value = row[y_col]
            
            # Calculate if point is within bounds using the original diagnostic controller logic
            if steady_state_threshold is not None and current_time_seconds >= start_time_seconds + time_to_achieve:
                # Use steady state threshold for points after the curve ends
                # Allow values within steady state threshold of the target value
                in_bounds = abs(actual_value - end_value) <= steady_state_threshold
            else:
                # Use regular threshold for points during the curve
                in_bounds = abs(actual_value - expected_value) <= threshold
            
            # Use diagnostic controller color coding
            if in_bounds:
                color = '#28a745'  # Green for Pass
                status = 'Pass'
            else:
                color = '#dc3545'  # Red for Fail
                status = 'Fail'
            
            # Add debugging for first few points
            if len(actual_colors) < 5:
                threshold_used = steady_state_threshold if (steady_state_threshold is not None and current_time_seconds >= start_time_seconds + time_to_achieve) else threshold
                print(f"Debug: Point {len(actual_colors)+1} - Time: {row[x_col]}, Value: {row[y_col]:.2f}, Expected: {expected_value:.2f}, Threshold: {threshold_used}, Diff: {abs(row[y_col] - expected_value):.2f}, InBounds: {in_bounds}, Status: {status}")
            
            actual_colors.append(color)
            actual_tooltips.append(f"Value: {row[y_col]:.2f}<br>Time: {row[x_col].strftime('%Y-%m-%d %H:%M:%S')}<br>Expected: {expected_value:.2f}<br>Status: {status}")
        except (ValueError, AttributeError, OSError) as e:
            # Skip invalid datetime values
            continue
    
    # Calculate status statistics
    pass_count = sum(1 for color in actual_colors if color == '#28a745')
    fail_count = sum(1 for color in actual_colors if color == '#dc3545')
    total_count = len(actual_colors)
    
    status_summary = {
        'total_points': total_count,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'pass_percentage': (pass_count / total_count * 100) if total_count > 0 else 0,
        'fail_percentage': (fail_count / total_count * 100) if total_count > 0 else 0
    }
    
    # Ensure all arrays are lists and not empty
    if not time_points:
        time_points = [start_time]
        expected_values = [start_value]
        upper_threshold = [start_value + threshold]
        lower_threshold = [start_value - threshold]
    
    if not actual_times:
        actual_times = [start_time]
        actual_values = [start_value]
        actual_colors = ['#28a745']
        actual_tooltips = [f"Value: {start_value:.2f}<br>Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}<br>Expected: {start_value:.2f}<br>Status: Pass"]
    
    return {
        'time_points': time_points,
        'expected_values': expected_values,
        'upper_threshold': upper_threshold,
        'lower_threshold': lower_threshold,
        'actual_times': actual_times,
        'actual_values': actual_values,
        'actual_colors': actual_colors,
        'actual_tooltips': actual_tooltips,
        'status_summary': status_summary
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            # Read Excel file
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
                sheets = ['Sheet1']
            else:
                # Get sheet names first
                xl = pd.ExcelFile(filepath)
                sheets = xl.sheet_names
                # Read the first sheet for basic info
                df = pd.read_excel(filepath, sheet_name=0)
            
            # Check if dataframe is empty
            if df.empty:
                return jsonify({'error': 'The file appears to be empty or contains no data'})
            
            # Get column information
            columns = df.columns.tolist()
            
            # For initial upload, just return basic info without parsing datetime
            # We'll parse datetime columns after the user selects a specific sheet
            
            return jsonify({
                'success': True,
                'filename': filename,
                'columns': columns,
                'sheets': sheets
            })
            
        except Exception as e:
            return jsonify({'error': f'Error reading file: {str(e)}'})
    
    return jsonify({'error': 'Invalid file type'})

@app.route('/get_sheet_names', methods=['POST'])
def get_sheet_names():
    data = request.get_json()
    filepath = os.path.join(UPLOAD_FOLDER, data['filename'])
    
    try:
        if filepath.endswith('.csv'):
            sheets = ['Sheet1']
        else:
            xl = pd.ExcelFile(filepath)
            sheets = xl.sheet_names
        
        return jsonify({'sheets': sheets})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/load_sheet_data', methods=['POST'])
def load_sheet_data():
    data = request.get_json()
    filepath = os.path.join(UPLOAD_FOLDER, data['filename'])
    sheet_name = data.get('sheet_name', 0)
    skip_rows = data.get('skip_rows', 0)
    
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, skiprows=skip_rows)
        else:
            df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows)
        
        # Check if dataframe is empty
        if df.empty:
            return jsonify({'error': 'The sheet appears to be empty or contains no data'})
        
        # Get column information
        columns = df.columns.tolist()
        
        # Try to identify datetime columns
        datetime_columns = []
        for col in columns:
            if parse_datetime_column(df, col):
                datetime_columns.append(col)
        
        # Detect and convert numeric columns
        numeric_columns = detect_and_convert_numeric_columns(df)
        
        # Add debugging information
        print(f"Debug: Found {len(datetime_columns)} datetime columns: {datetime_columns}")
        print(f"Debug: Found {len(numeric_columns)} numeric columns: {numeric_columns}")
        print(f"Debug: Total columns: {len(columns)}")
        print(f"Debug: Skip rows: {skip_rows}")
        
        # Clean the dataframe
        df_clean = clean_dataframe(df, datetime_columns, numeric_columns)
        
        print(f"Debug: After cleaning, dataframe has {len(df_clean)} rows")
        
        if df_clean.empty:
            return jsonify({'error': 'No valid data found after cleaning. Please check your sheet for missing or invalid values.'})
        
        return jsonify({
            'success': True,
            'columns': columns,
            'numeric_columns': numeric_columns,
            'datetime_columns': datetime_columns,
            'preview': df_clean.head(10).to_dict('records')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    data = request.get_json()
    
    try:
        # Load the data
        filepath = os.path.join(UPLOAD_FOLDER, data['filename'])
        sheet_name = data.get('sheet_name', 0)
        skip_rows = data.get('skip_rows', 0)
        
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, skiprows=skip_rows)
        else:
            df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows)
        
        # Parse datetime column
        x_col = data['x_axis']
        y_col = data['y_axis']
        
        if not parse_datetime_column(df, x_col):
            return jsonify({'error': f'Could not parse datetime column: {x_col}. Please ensure the column contains valid datetime values.'})
        
        # Clean the data
        datetime_columns = [x_col]
        numeric_columns = [y_col]
        df_clean = clean_dataframe(df, datetime_columns, numeric_columns)
        
        if df_clean.empty:
            return jsonify({'error': 'No valid data points found after cleaning. Please check your data for missing or invalid values.'})
        
        # Parse parameters
        start_time_str = data['start_time']
        end_time_str = data['end_time']
        data_start_time_str = data.get('data_start_time')
        data_end_time_str = data.get('data_end_time')
        start_value = float(data['start_value'])
        end_value = float(data['end_value'])
        threshold = float(data['threshold'])
        steady_state_threshold = float(data['steady_state_threshold']) if data['steady_state_threshold'] else None
        time_to_achieve = float(data['time_to_achieve'])
        
        # Parse times
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        
        # Parse optional data filter times
        data_start_time = None
        data_end_time = None
        if data_start_time_str:
            data_start_time = datetime.fromisoformat(data_start_time_str.replace('Z', '+00:00'))
        if data_end_time_str:
            data_end_time = datetime.fromisoformat(data_end_time_str.replace('Z', '+00:00'))
        
        # Add debugging information
        print(f"Debug: Start value: {start_value}, End value: {end_value}")
        print(f"Debug: Start time: {start_time}, End time: {end_time}")
        print(f"Debug: Data filter - Start: {data_start_time}, End: {data_end_time}")
        print(f"Debug: Time to achieve: {time_to_achieve}")
        print(f"Debug: Threshold: {threshold}")
        print(f"Debug: Steady state threshold: {steady_state_threshold}")
        
        # Check if start and end values are the same
        if start_value == end_value:
            print(f"Warning: Start and End values are the same ({start_value}). Expected curve will be horizontal.")
        
        # Generate graph data
        graph_data = create_graph_data(df_clean, x_col, y_col, start_time, end_time, 
                                     start_value, end_value, threshold, 
                                     steady_state_threshold, time_to_achieve,
                                     data_start_time, data_end_time)
        
        if not graph_data:
            return jsonify({'error': 'No data points in the specified time range'})
        
        # Debug: Check the structure of graph_data
        print(f"Debug: Graph data keys: {list(graph_data.keys())}")
        for key, value in graph_data.items():
            if key != 'status_summary':
                print(f"Debug: {key} type: {type(value)}, length: {len(value) if hasattr(value, '__len__') else 'N/A'}")
                if hasattr(value, '__len__') and len(value) > 0:
                    print(f"Debug: {key} first item: {value[0]}, type: {type(value[0])}")
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Ensure all data is properly formatted as lists
        time_points = graph_data['time_points'] if isinstance(graph_data['time_points'], list) else [graph_data['time_points']]
        expected_values = graph_data['expected_values'] if isinstance(graph_data['expected_values'], list) else [graph_data['expected_values']]
        upper_threshold = graph_data['upper_threshold'] if isinstance(graph_data['upper_threshold'], list) else [graph_data['upper_threshold']]
        lower_threshold = graph_data['lower_threshold'] if isinstance(graph_data['lower_threshold'], list) else [graph_data['lower_threshold']]
        actual_times = graph_data['actual_times'] if isinstance(graph_data['actual_times'], list) else [graph_data['actual_times']]
        actual_values = graph_data['actual_values'] if isinstance(graph_data['actual_values'], list) else [graph_data['actual_values']]
        actual_colors = graph_data['actual_colors'] if isinstance(graph_data['actual_colors'], list) else [graph_data['actual_colors']]
        actual_tooltips = graph_data['actual_tooltips'] if isinstance(graph_data['actual_tooltips'], list) else [graph_data['actual_tooltips']]
        
        # Convert datetime objects to strings for Plotly
        time_points_str = [t.strftime('%Y-%m-%d %H:%M:%S') if hasattr(t, 'strftime') else str(t) for t in time_points]
        actual_times_str = [t.strftime('%Y-%m-%d %H:%M:%S') if hasattr(t, 'strftime') else str(t) for t in actual_times]
        
        # Ensure all values are numeric
        expected_values = [float(v) if v is not None else 0.0 for v in expected_values]
        upper_threshold = [float(v) if v is not None else 0.0 for v in upper_threshold]
        lower_threshold = [float(v) if v is not None else 0.0 for v in lower_threshold]
        actual_values = [float(v) if v is not None else 0.0 for v in actual_values]
        
        # Expected curve
        if len(time_points_str) > 0 and len(expected_values) > 0:
            fig.add_trace(go.Scatter(
                x=time_points_str,
                y=expected_values,
                mode='lines',
                name='Expected Curve',
                line=dict(color='blue', width=2)
            ))
        
        # Threshold lines
        if len(time_points_str) > 0 and len(upper_threshold) > 0:
            fig.add_trace(go.Scatter(
                x=time_points_str,
                y=upper_threshold,
                mode='lines',
                name='Upper Threshold',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        if len(time_points_str) > 0 and len(lower_threshold) > 0:
            fig.add_trace(go.Scatter(
                x=time_points_str,
                y=lower_threshold,
                mode='lines',
                name='Lower Threshold',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        # Actual data points - separate pass and fail points
        if len(actual_times_str) > 0 and len(actual_values) > 0:
            # Separate pass and fail points
            pass_times = []
            pass_values = []
            pass_tooltips = []
            fail_times = []
            fail_values = []
            fail_tooltips = []
            
            for i, color in enumerate(actual_colors):
                if color == '#28a745':  # Green - Pass
                    pass_times.append(actual_times_str[i])
                    pass_values.append(actual_values[i])
                    pass_tooltips.append(actual_tooltips[i])
                else:  # Red - Fail
                    fail_times.append(actual_times_str[i])
                    fail_values.append(actual_values[i])
                    fail_tooltips.append(actual_tooltips[i])
            
            # Add pass points
            if pass_times and pass_values:
                fig.add_trace(go.Scatter(
                    x=pass_times,
                    y=pass_values,
                    mode='markers',
                    name='Pass',
                    marker=dict(
                        color='#28a745',
                        size=6,
                        symbol='circle',
                        opacity=0.7,
                        line=dict(width=0.5, color='#1e7e34')
                    ),
                    text=pass_tooltips,
                    hoverinfo='text'
                ))
            
            # Add fail points
            if fail_times and fail_values:
                fig.add_trace(go.Scatter(
                    x=fail_times,
                    y=fail_values,
                    mode='markers',
                    name='Fail',
                    marker=dict(
                        color='#dc3545',
                        size=8,
                        symbol='x',
                        opacity=0.9,
                        line=dict(width=1, color='#c82333')
                    ),
                    text=fail_tooltips,
                    hoverinfo='text'
                ))
        
        # Update layout
        fig.update_layout(
            title='Diagnostic Data Analysis',
            xaxis_title='Time',
            yaxis_title='Value',
            hovermode='closest',
            legend=dict(orientation='h', x=0.5, xanchor='center', y=1.15),
            margin=dict(l=60, r=30, t=30, b=60),
            title_font_color='#003366',
            title_font_size=18
        )
        
        # Convert to JSON
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        # Include status summary in the response
        response_data = {
            'success': True,
            'graph': graph_json,
            'status_summary': graph_data.get('status_summary', {})
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        print(f"Error in generate_graph: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error generating graph: {str(e)}'})

@app.route('/download_standalone_html', methods=['POST'])
def download_standalone_html():
    data = request.get_json()
    
    try:
        # Get the current graph data
        filepath = os.path.join(UPLOAD_FOLDER, data['filename'])
        sheet_name = data.get('sheet_name', 0)
        skip_rows = data.get('skip_rows', 0)
        
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, skiprows=skip_rows)
        else:
            df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows)
        
        # Parse datetime column
        x_col = data['x_axis']
        y_col = data['y_axis']
        
        if not parse_datetime_column(df, x_col):
            return jsonify({'error': f'Could not parse datetime column: {x_col}'})
        
        # Clean the data
        datetime_columns = [x_col]
        numeric_columns = [y_col]
        df_clean = clean_dataframe(df, datetime_columns, numeric_columns)
        
        if df_clean.empty:
            return jsonify({'error': 'No valid data points found after cleaning'})
        
        # Parse parameters
        start_time_str = data['start_time']
        end_time_str = data['end_time']
        data_start_time_str = data.get('data_start_time')
        data_end_time_str = data.get('data_end_time')
        start_value = float(data['start_value'])
        end_value = float(data['end_value'])
        threshold = float(data['threshold'])
        steady_state_threshold = float(data['steady_state_threshold']) if data['steady_state_threshold'] else None
        time_to_achieve = float(data['time_to_achieve'])
        
        # Parse times
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        
        # Parse optional data filter times
        data_start_time = None
        data_end_time = None
        if data_start_time_str:
            data_start_time = datetime.fromisoformat(data_start_time_str.replace('Z', '+00:00'))
        if data_end_time_str:
            data_end_time = datetime.fromisoformat(data_end_time_str.replace('Z', '+00:00'))
        
        # Generate graph data
        graph_data = create_graph_data(df_clean, x_col, y_col, start_time, end_time, 
                                     start_value, end_value, threshold, 
                                     steady_state_threshold, time_to_achieve,
                                     data_start_time, data_end_time)
        
        if not graph_data:
            return jsonify({'error': 'No data points in the specified time range'})
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Ensure all data is properly formatted as lists
        time_points = graph_data['time_points'] if isinstance(graph_data['time_points'], list) else [graph_data['time_points']]
        expected_values = graph_data['expected_values'] if isinstance(graph_data['expected_values'], list) else [graph_data['expected_values']]
        upper_threshold = graph_data['upper_threshold'] if isinstance(graph_data['upper_threshold'], list) else [graph_data['upper_threshold']]
        lower_threshold = graph_data['lower_threshold'] if isinstance(graph_data['lower_threshold'], list) else [graph_data['lower_threshold']]
        actual_times = graph_data['actual_times'] if isinstance(graph_data['actual_times'], list) else [graph_data['actual_times']]
        actual_values = graph_data['actual_values'] if isinstance(graph_data['actual_values'], list) else [graph_data['actual_values']]
        actual_colors = graph_data['actual_colors'] if isinstance(graph_data['actual_colors'], list) else [graph_data['actual_colors']]
        actual_tooltips = graph_data['actual_tooltips'] if isinstance(graph_data['actual_tooltips'], list) else [graph_data['actual_tooltips']]
        
        # Convert datetime objects to strings for Plotly
        time_points_str = [t.strftime('%Y-%m-%d %H:%M:%S') if hasattr(t, 'strftime') else str(t) for t in time_points]
        actual_times_str = [t.strftime('%Y-%m-%d %H:%M:%S') if hasattr(t, 'strftime') else str(t) for t in actual_times]
        
        # Ensure all values are numeric
        expected_values = [float(v) if v is not None else 0.0 for v in expected_values]
        upper_threshold = [float(v) if v is not None else 0.0 for v in upper_threshold]
        lower_threshold = [float(v) if v is not None else 0.0 for v in lower_threshold]
        actual_values = [float(v) if v is not None else 0.0 for v in actual_values]
        
        # Expected curve
        if len(time_points_str) > 0 and len(expected_values) > 0:
            fig.add_trace(go.Scatter(
                x=time_points_str,
                y=expected_values,
                mode='lines',
                name='Expected Curve',
                line=dict(color='blue', width=2)
            ))
        
        # Threshold lines
        if len(time_points_str) > 0 and len(upper_threshold) > 0:
            fig.add_trace(go.Scatter(
                x=time_points_str,
                y=upper_threshold,
                mode='lines',
                name='Upper Threshold',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        if len(time_points_str) > 0 and len(lower_threshold) > 0:
            fig.add_trace(go.Scatter(
                x=time_points_str,
                y=lower_threshold,
                mode='lines',
                name='Lower Threshold',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        # Actual data points - separate pass and fail points
        if len(actual_times_str) > 0 and len(actual_values) > 0:
            # Separate pass and fail points
            pass_times = []
            pass_values = []
            pass_tooltips = []
            fail_times = []
            fail_values = []
            fail_tooltips = []
            
            for i, color in enumerate(actual_colors):
                if color == '#28a745':  # Green - Pass
                    pass_times.append(actual_times_str[i])
                    pass_values.append(actual_values[i])
                    pass_tooltips.append(actual_tooltips[i])
                else:  # Red - Fail
                    fail_times.append(actual_times_str[i])
                    fail_values.append(actual_values[i])
                    fail_tooltips.append(actual_tooltips[i])
            
            # Add pass points
            if pass_times and pass_values:
                fig.add_trace(go.Scatter(
                    x=pass_times,
                    y=pass_values,
                    mode='markers',
                    name='Pass',
                    marker=dict(
                        color='#28a745',
                        size=6,
                        symbol='circle',
                        opacity=0.7,
                        line=dict(width=0.5, color='#1e7e34')
                    ),
                    text=pass_tooltips,
                    hoverinfo='text'
                ))
            
            # Add fail points
            if fail_times and fail_values:
                fig.add_trace(go.Scatter(
                    x=fail_times,
                    y=fail_values,
                    mode='markers',
                    name='Fail',
                    marker=dict(
                        color='#dc3545',
                        size=8,
                        symbol='x',
                        opacity=0.9,
                        line=dict(width=1, color='#c82333')
                    ),
                    text=fail_tooltips,
                    hoverinfo='text'
                ))
        
        # Update layout
        fig.update_layout(
            title='Threshold Analysis Results',
            xaxis_title='Time',
            yaxis_title='Value',
            hovermode='closest',
            legend=dict(orientation='h', x=0.5, xanchor='center', y=1.15),
            margin=dict(l=60, r=30, t=30, b=60),
            title_font_color='#003366',
            title_font_size=18
        )
        
        # Generate standalone HTML
        html_content = fig.to_html(
            include_plotlyjs=True,
            full_html=True,
            config={'displayModeBar': True, 'displaylogo': False}
        )
        
        # Create a more complete standalone HTML with styling
        standalone_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Threshold Analysis Results</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #003366 0%, #0066cc 100%);
            color: white;
            padding: 30px 0;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .status-summary {{
            margin-bottom: 30px;
        }}
        .status-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .text-pass {{
            color: #28a745 !important;
        }}
        .text-fail {{
            color: #dc3545 !important;
        }}
        .text-primary {{
            color: #007bff !important;
        }}
        .text-info {{
            color: #17a2b8 !important;
        }}
        .graph-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header text-center">
            <h1><i class="fas fa-chart-line me-3"></i>Threshold Analysis Results</h1>
            <p class="lead mb-0">Interactive data visualization with pass/fail analysis</p>
        </div>
        
        <div class="status-summary">
            <div class="row">
                <div class="col-md-3">
                    <div class="status-card">
                        <h5 class="text-pass">
                            <i class="fas fa-check-circle me-2"></i>Pass
                        </h5>
                        <h3 class="text-pass">{graph_data.get('status_summary', {}).get('pass_count', 0)}</h3>
                        <p class="text-muted">{graph_data.get('status_summary', {}).get('pass_percentage', 0):.1f}%</p>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="status-card">
                        <h5 class="text-fail">
                            <i class="fas fa-times-circle me-2"></i>Fail
                        </h5>
                        <h3 class="text-fail">{graph_data.get('status_summary', {}).get('fail_count', 0)}</h3>
                        <p class="text-muted">{graph_data.get('status_summary', {}).get('fail_percentage', 0):.1f}%</p>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="status-card">
                        <h5 class="text-primary">
                            <i class="fas fa-chart-bar me-2"></i>Total
                        </h5>
                        <h3 class="text-primary">{graph_data.get('status_summary', {}).get('total_points', 0)}</h3>
                        <p class="text-muted">Data Points</p>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="status-card">
                        <h5 class="text-info">
                            <i class="fas fa-percentage me-2"></i>Success Rate
                        </h5>
                        <h3 class="text-info">{graph_data.get('status_summary', {}).get('pass_percentage', 0):.1f}%</h3>
                        <p class="text-muted">Overall</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="graph-container">
            {html_content}
        </div>
        
        <div class="footer">
            <p>Generated by Data Analysis Tools - Threshold Analysis</p>
            <p>Analysis Parameters: Start Value: {start_value}, End Value: {end_value}, Threshold: {threshold}, Time to Achieve: {time_to_achieve}s</p>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        """
        
        return jsonify({
            'success': True,
            'html_content': standalone_html
        })
        
    except Exception as e:
        import traceback
        print(f"Error in download_standalone_html: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error generating standalone HTML: {str(e)}'})

@app.route('/graph_generator')
def graph_generator():
    return render_template('graph_generator.html')

@app.route('/generate_simple_graph', methods=['POST'])
def generate_simple_graph():
    data = request.get_json()
    
    try:
        # Load the data
        filepath = os.path.join(UPLOAD_FOLDER, data['filename'])
        sheet_name = data.get('sheet_name', 0)
        skip_rows = data.get('skip_rows', [])
        
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, skiprows=skip_rows)
        else:
            df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows)
        
        # Drop completely empty rows
        df.dropna(how='all', inplace=True)
        
        # Get column information
        columns = df.columns.tolist()
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        datetime_columns = []
        
        # Detect datetime columns
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    pd.to_datetime(df[col].iloc[0:10], errors='raise')
                    datetime_columns.append(col)
                except:
                    pass
        
        return jsonify({
            'success': True,
            'columns': columns,
            'numeric_columns': numeric_columns,
            'datetime_columns': datetime_columns,
            'total_rows': len(df)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in generate_simple_graph: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error loading data: {str(e)}'})

@app.route('/create_simple_graph', methods=['POST'])
def create_simple_graph():
    data = request.get_json()
    
    try:
        # Load the data
        filepath = os.path.join(UPLOAD_FOLDER, data['filename'])
        sheet_name = data.get('sheet_name', 0)
        skip_rows = data.get('skip_rows', [])
        
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, skiprows=skip_rows)
        else:
            df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows)
        
        # Drop completely empty rows
        df.dropna(how='all', inplace=True)
        
        # Get selected columns
        x_col = data['x_axis']
        y_cols = data['y_axes']
        
        # Create the plot exactly like the original Graph Generator.py
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
        
        # Convert to JSON
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({
            'success': True,
            'graph': graph_json
        })
        
    except Exception as e:
        import traceback
        print(f"Error in create_simple_graph: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error creating graph: {str(e)}'})

@app.route('/download_simple_graph_html', methods=['POST'])
def download_simple_graph_html():
    data = request.get_json()
    
    try:
        # Load the data
        filepath = os.path.join(UPLOAD_FOLDER, data['filename'])
        sheet_name = data.get('sheet_name', 0)
        skip_rows = data.get('skip_rows', [])
        
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, skiprows=skip_rows)
        else:
            df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows)
        
        # Drop completely empty rows
        df.dropna(how='all', inplace=True)
        
        # Get selected columns
        x_col = data['x_axis']
        y_cols = data['y_axes']
        
        # Create the plot exactly like the original Graph Generator.py
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
        
        # Generate HTML exactly like the original Graph Generator.py
        html_content = fig.to_html(
            include_plotlyjs=True,
            full_html=True,
            config={'displayModeBar': True, 'displaylogo': False}
        )
        
        return jsonify({
            'success': True,
            'html_content': html_content
        })
        
    except Exception as e:
        import traceback
        print(f"Error in download_simple_graph_html: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Error generating standalone HTML: {str(e)}'})

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003) 