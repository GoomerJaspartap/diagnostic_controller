#!/usr/bin/env python3

# Script to fix the remaining check_limits calls in read_modbus_data.py

def fix_check_limits_calls():
    """Fix the remaining check_limits calls to include upper_limit and lower_limit parameters"""
    
    # Read the file
    with open('read_modbus_data.py', 'r') as f:
        content = f.read()
    
    # Replace the remaining calls
    # First call around line 611
    content = content.replace(
        'status = check_limits(value, diag[15], diag[16], diag[17], diag[18], enabled_at)',
        'status = check_limits(value, diag[15], diag[16], diag[17], diag[18], enabled_at, diag[20], diag[21])'
    )
    
    # Second call around line 695
    content = content.replace(
        'status = check_limits(value, diag[15], diag[16], diag[17], diag[18], enabled_at)',
        'status = check_limits(value, diag[15], diag[16], diag[17], diag[18], enabled_at, diag[20], diag[21])'
    )
    
    # Write back to file
    with open('read_modbus_data.py', 'w') as f:
        f.write(content)
    
    print("Fixed check_limits calls in read_modbus_data.py")

if __name__ == "__main__":
    fix_check_limits_calls() 