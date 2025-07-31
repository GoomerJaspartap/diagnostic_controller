#!/usr/bin/env python3
"""
Test script to verify the threshold analysis fix
"""

import pandas as pd
import requests
import json

def test_threshold_analysis():
    """Test the threshold analysis with the fixed cleaning logic"""
    
    print("🔍 Testing Threshold Analysis Fix...")
    
    # Test data
    test_data = {
        "filename": "jass_test.xlsx",
        "sheet_name": "1 s",
        "skip_rows": 0
    }
    
    print(f"\n📊 Test Data:")
    print(f"   File: {test_data['filename']}")
    print(f"   Sheet: {test_data['sheet_name']}")
    print(f"   Skip rows: {test_data['skip_rows']}")
    
    # Test the load_sheet_data endpoint
    print("\n1. Testing load_sheet_data endpoint...")
    response = requests.post("http://localhost:5003/load_sheet_data", 
                           json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Threshold analysis successful!")
            print(f"   Columns: {len(data['columns'])}")
            print(f"   Numeric columns: {len(data['numeric_columns'])}")
            print(f"   Datetime columns: {len(data['datetime_columns'])}")
            print(f"   Preview rows: {len(data['preview'])}")
            
            if data['preview']:
                print(f"   First row sample: {data['preview'][0]}")
        else:
            print(f"❌ Threshold analysis failed: {data.get('error')}")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"   Response: {response.text}")

if __name__ == "__main__":
    test_threshold_analysis() 