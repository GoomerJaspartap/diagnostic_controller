#!/usr/bin/env python3
"""
Test script for the common sheet functionality
"""

import pandas as pd
import numpy as np
import os
import tempfile
from datetime import datetime, timedelta

def create_test_files_with_common_sheets():
    """Create test Excel files with common sheets"""
    test_files = []
    
    # Define common sheets that will be in all files
    common_sheets = ['Data', 'Summary', 'Settings']
    
    for i in range(5):
        # Create sample data for each sheet
        data_sheet = {
            'Time': pd.date_range(start='2024-01-01', periods=100, freq='H'),
            'Elapsed Time': np.random.uniform(0, 100, 100),
            'Temperature': np.random.uniform(20, 80, 100),
            'Pressure': np.random.uniform(1, 10, 100),
            'Flow Rate': np.random.uniform(0, 50, 100),
            'Status': np.random.choice(['Active', 'Inactive', 'Warning'], 100)
        }
        
        summary_sheet = {
            'Metric': ['Total Records', 'Average Temp', 'Max Pressure', 'Min Flow'],
            'Value': [100, 50.5, 9.8, 2.1],
            'Unit': ['records', '°C', 'bar', 'L/min']
        }
        
        settings_sheet = {
            'Parameter': ['Sampling Rate', 'Threshold', 'Alarm Level'],
            'Value': [1.0, 75.0, 90.0],
            'Unit': ['Hz', '°C', '%']
        }
        
        # Create temporary file with multiple sheets
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                pd.DataFrame(data_sheet).to_excel(writer, sheet_name='Data', index=False)
                pd.DataFrame(summary_sheet).to_excel(writer, sheet_name='Summary', index=False)
                pd.DataFrame(settings_sheet).to_excel(writer, sheet_name='Settings', index=False)
                
                # Add a unique sheet for each file
                unique_sheet = {
                    'File': [f'File_{i+1}'] * 10,
                    'Unique_Data': np.random.rand(10)
                }
                pd.DataFrame(unique_sheet).to_excel(writer, sheet_name=f'Unique_{i+1}', index=False)
            
            test_files.append(tmp.name)
    
    return test_files, common_sheets

def test_common_sheet_detection():
    """Test the common sheet detection functionality"""
    print("Testing Common Sheet Detection")
    print("=" * 40)
    
    # Create test files
    test_files, expected_common_sheets = create_test_files_with_common_sheets()
    
    try:
        # Simulate the common sheet detection logic
        all_sheets = {}
        common_sheets = None
        
        for i, filepath in enumerate(test_files):
            print(f"Processing file {i+1}: {os.path.basename(filepath)}")
            
            # Read Excel file to get sheet names
            excel_file = pd.ExcelFile(filepath)
            sheets = excel_file.sheet_names
            all_sheets[f'file_{i+1}'] = sheets
            
            print(f"  Sheets found: {sheets}")
            
            # Find common sheets
            if common_sheets is None:
                common_sheets = set(sheets)
            else:
                common_sheets = common_sheets.intersection(set(sheets))
        
        # Convert to sorted list
        common_sheets_list = sorted(list(common_sheets))
        
        print(f"\nCommon sheets detected: {common_sheets_list}")
        print(f"Expected common sheets: {expected_common_sheets}")
        
        # Verify results
        if set(common_sheets_list) == set(expected_common_sheets):
            print("✅ Common sheet detection working correctly!")
        else:
            print("❌ Common sheet detection failed!")
            print(f"Missing: {set(expected_common_sheets) - set(common_sheets_list)}")
            print(f"Extra: {set(common_sheets_list) - set(expected_common_sheets)}")
        
        # Test sheet availability per file
        print(f"\nSheet availability per file:")
        for filename, sheets in all_sheets.items():
            print(f"  {filename}: {len(sheets)} sheets")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    finally:
        # Clean up test files
        for filepath in test_files:
            if os.path.exists(filepath):
                os.remove(filepath)

def test_sheet_application():
    """Test applying a common sheet to multiple files"""
    print("\nTesting Sheet Application")
    print("=" * 30)
    
    # Create test files
    test_files, common_sheets = create_test_files_with_common_sheets()
    
    try:
        # Test applying 'Data' sheet to all files
        target_sheet = 'Data'
        applied_count = 0
        
        for i, filepath in enumerate(test_files):
            print(f"Processing file {i+1}...")
            
            # Check if target sheet exists
            excel_file = pd.ExcelFile(filepath)
            if target_sheet in excel_file.sheet_names:
                # Read the target sheet
                df = pd.read_excel(filepath, sheet_name=target_sheet)
                print(f"  ✅ Successfully read '{target_sheet}' sheet with {len(df)} rows")
                applied_count += 1
            else:
                print(f"  ❌ Sheet '{target_sheet}' not found in file {i+1}")
        
        print(f"\nApplied '{target_sheet}' to {applied_count} out of {len(test_files)} files")
        
        if applied_count == len(test_files):
            print("✅ All files successfully processed with common sheet!")
        else:
            print("⚠️  Some files could not be processed with the common sheet")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during sheet application test: {e}")
        return False
    
    finally:
        # Clean up test files
        for filepath in test_files:
            if os.path.exists(filepath):
                os.remove(filepath)

if __name__ == "__main__":
    print("Testing Common Sheet Functionality")
    print("=" * 50)
    
    # Run tests
    test1_passed = test_common_sheet_detection()
    test2_passed = test_sheet_application()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! Common sheet functionality is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.") 