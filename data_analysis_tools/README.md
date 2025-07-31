# Data Analysis Tools

A comprehensive web application for Excel data visualization and analysis with threshold-based color coding.

## Features

### Threshold Analysis
- Upload Excel files with drag-and-drop interface
- Specify sheet names and rows to skip
- Select X and Y axis columns
- Set start/end time and values for expected curves
- Configure thresholds for pass/fail analysis
- Generate color-coded graphs (green for pass, red for fail)
- Download standalone HTML files

### Graph Generator
- Simple interactive graph generation
- Upload Excel files and select columns
- Generate line plots with multiple Y-axis columns
- Download standalone HTML files
- Clean, minimal interface matching original Graph Generator.py

### Data Combiner
- Upload multiple Excel/CSV files simultaneously
- Select specific sheets for Excel files (.xlsx, .xls)
- Automatically combine data with column alignment
- Preview combined data before download
- Download combined dataset as CSV file
- Handles mixed file formats seamlessly

### Data Cleanup
- Upload Excel files and select specific sheets
- Configurable time intervals (e.g., 60 seconds for minute marks)
- Flexible sample range configuration
- Time-based sample range calculation
- Aggregate data by averaging samples at interval points
- Preview processed data and download cleaned CSV
- Reduces data size while preserving key trends

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5003
```

## Usage

### Threshold Analysis
1. Upload an Excel file using the drag-and-drop area
2. Select the sheet containing your data
3. Configure the parameters:
   - X-axis column (time/datetime)
   - Y-axis column (values to analyze)
   - Start/end time and values for expected curve
   - Threshold values
4. Generate the graph to see color-coded results
5. Download standalone HTML for sharing

### Graph Generator
1. Upload an Excel file
2. Select the sheet and configure skip rows
3. Choose X-axis and Y-axis columns
4. Generate the interactive graph
5. Download standalone HTML file

### Data Combiner
1. Upload multiple Excel/CSV files using drag-and-drop
2. For Excel files, select the sheet containing your data
3. Review the file list and configurations
4. Click "Combine Data" to merge all files
5. Preview the combined dataset
6. Download the combined CSV file

### Data Cleanup
1. Upload an Excel file and select the sheet containing your data
2. Configure the time interval (e.g., 60 seconds for minute marks)
3. Set the sample range or use time-based calculation
4. Review the calculation preview
5. Click "Process Data" to aggregate and clean the data
6. Preview the cleaned data and download the CSV file

## File Structure

```
data_analysis_tools/
├── app.py                 # Main Flask application
├── templates/             # HTML templates
│   ├── index.html        # Threshold Analysis page
│   ├── graph_generator.html # Graph Generator page
│   ├── data_combiner.html # Data Combiner page
│   └── data_cleanup.html # Data Cleanup page
├── static/               # Static files (CSS, JS, images)
├── uploads/              # Uploaded files storage
└── requirements.txt      # Python dependencies
```

## Technologies Used

- **Backend**: Flask, Pandas, Plotly
- **Frontend**: Bootstrap 5, Plotly.js, JavaScript
- **Data Processing**: Pandas for Excel file handling
- **Visualization**: Plotly for interactive graphs

## License

This project is part of the diagnostic controller system. 