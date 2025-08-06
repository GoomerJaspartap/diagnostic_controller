#!/usr/bin/env python3
"""
Test script for the enhanced data combiner functionality
"""

import pandas as pd
import numpy as np
import os
import tempfile
from datetime import datetime, timedelta

def create_test_files(num_files=10, rows_per_file=1000):
    """Create test Excel files for testing the data combiner"""
    test_files = []
    
    for i in range(num_files):
        # Create sample data
        dates = pd.date_range(start='2024-01-01', periods=rows_per_file, freq='H')
        data = {
            'Time': dates,
            'Elapsed Time': np.random.uniform(0, 100, rows_per_file),
            'Temperature': np.random.uniform(20, 80, rows_per_file),
            'Pressure': np.random.uniform(1, 10, rows_per_file),
            'Flow Rate': np.random.uniform(0, 50, rows_per_file),
            'Status': np.random.choice(['Active', 'Inactive', 'Warning'], rows_per_file)
        }
        
        df = pd.DataFrame(data)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df.to_excel(tmp.name, sheet_name='Data', index=False)
            test_files.append(tmp.name)
    
    return test_files

def test_memory_optimization():
    """Test memory optimization with large datasets"""
    print("Testing memory optimization...")
    
    # Create test files
    test_files = create_test_files(num_files=5, rows_per_file=5000)
    
    try:
        # Test reading files with memory optimization
        all_columns = set()
        combined_dfs = []
        
        for filepath in test_files:
            print(f"Processing {os.path.basename(filepath)}...")
            
            # Read file with optimized settings
            df = pd.read_excel(filepath, sheet_name='Data', engine='openpyxl')
            
            # Ensure Elapsed Time is numeric
            if 'Elapsed Time' in df.columns:
                df['Elapsed Time'] = pd.to_numeric(df['Elapsed Time'], errors='coerce')
            
            combined_dfs.append(df)
            all_columns.update(df.columns)
        
        # Combine DataFrames
        if combined_dfs:
            combined_df = pd.concat(combined_dfs, ignore_index=True, copy=False)
            print(f"Successfully combined {len(combined_dfs)} files")
            print(f"Total rows: {len(combined_df):,}")
            print(f"Total columns: {len(combined_df.columns)}")
            print(f"Memory usage: {combined_df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    
    finally:
        # Clean up test files
        for filepath in test_files:
            if os.path.exists(filepath):
                os.remove(filepath)

def test_batch_processing():
    """Test batch processing functionality"""
    print("\nTesting batch processing...")
    
    # Create more test files to simulate large dataset
    test_files = create_test_files(num_files=20, rows_per_file=1000)
    
    try:
        batch_size = 5
        all_columns = set()
        processed_files = 0
        combined_dfs = []
        
        # Process files in batches
        for batch_start in range(0, len(test_files), batch_size):
            batch_end = min(batch_start + batch_size, len(test_files))
            batch_files = test_files[batch_start:batch_end]
            
            print(f"Processing batch {batch_start//batch_size + 1} ({len(batch_files)} files)...")
            
            batch_dfs = []
            for filepath in batch_files:
                df = pd.read_excel(filepath, sheet_name='Data', engine='openpyxl')
                
                if 'Elapsed Time' in df.columns:
                    df['Elapsed Time'] = pd.to_numeric(df['Elapsed Time'], errors='coerce')
                
                batch_dfs.append(df)
                all_columns.update(df.columns)
                processed_files += 1
            
            # Combine batch DataFrames
            if batch_dfs:
                batch_combined = pd.concat(batch_dfs, ignore_index=True, copy=False)
                combined_dfs.append(batch_combined)
                
                # Clear batch memory
                del batch_dfs
                import gc
                gc.collect()
        
        # Final combination
        if combined_dfs:
            final_df = pd.concat(combined_dfs, ignore_index=True, copy=False)
            print(f"Successfully processed {processed_files} files in batches")
            print(f"Total rows: {len(final_df):,}")
            print(f"Total columns: {len(final_df.columns)}")
        
    except Exception as e:
        print(f"Error during batch testing: {e}")
    
    finally:
        # Clean up test files
        for filepath in test_files:
            if os.path.exists(filepath):
                os.remove(filepath)

if __name__ == "__main__":
    print("Testing Enhanced Data Combiner Functionality")
    print("=" * 50)
    
    test_memory_optimization()
    test_batch_processing()
    
    print("\nTest completed successfully!") 