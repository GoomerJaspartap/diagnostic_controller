import sqlite3
import datetime
from typing import List, Dict, Tuple, Optional
from AlertAPI import send_alert

def get_db_connection():
    conn = sqlite3.connect('diagnostics.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_contacts() -> Tuple[List[str], List[str]]:
    """
    Get all contact emails and phone numbers from the database.
    
    Returns:
        Tuple[List[str], List[str]]: (emails, phone_numbers)
    """
    conn = get_db_connection()
    try:
        contacts = conn.execute('SELECT email, phone FROM contacts').fetchall()
        emails = [c['email'] for c in contacts]
        phone_numbers = [c['phone'] for c in contacts]
        return emails, phone_numbers
    finally:
        conn.close()

def get_diagnostic_details(code: str) -> Optional[Dict]:
    """
    Get full details of a diagnostic code including description.
    
    Args:
        code (str): The diagnostic code to look up
    
    Returns:
        Optional[Dict]: Dictionary containing diagnostic details
    """
    conn = get_db_connection()
    try:
        diagnostic = conn.execute('''
            SELECT code, description, state, last_failure, type
            FROM diagnostic_codes 
            WHERE code = ? AND enabled = 1
        ''', (code,)).fetchone()
        return dict(diagnostic) if diagnostic else None
    finally:
        conn.close()

def send_diagnostic_alert(diagnostics: List[Dict]) -> None:
    """
    Send alerts for diagnostic updates.
    
    Args:
        diagnostics (List[Dict]): List of diagnostic updates
    """
    if not diagnostics:
        return
        
    # Get contact information
    emails, phone_numbers = get_contacts()
    
    # Prepare alert message
    subject = "Fault Detected"
    message = "Fault Detected"
    
    # Format table data for the alert
    table_data = []
    for d in diagnostics:
        details = get_diagnostic_details(d['code'])
        if details:
            table_data.append({
                'code': d['code'],
                'description': details['description'],
                'state': d['state'],
                'last_failure': d['last_failure'],
                'history_count': d['history_count'],
                'type': details['type']
            })
    
    # Send alerts
    if table_data:
        send_alert(emails, phone_numbers, subject, message, table_data)

def get_enabled_diagnostics() -> List[Dict]:
    """
    Get all enabled diagnostic codes and their current states.
    
    Returns:
        List[Dict]: List of dictionaries containing diagnostic information
    """
    conn = get_db_connection()
    try:
        diagnostics = conn.execute('''
            SELECT code, description, state, last_failure, history_count, type
            FROM diagnostic_codes 
            WHERE enabled = 1
        ''').fetchall()
        return [dict(d) for d in diagnostics]
    finally:
        conn.close()

def update_diagnostic(code: str, new_state: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Update a single diagnostic code's state and history.
    
    Args:
        code (str): The diagnostic code to update
        new_state (str): The new state ('Pass', 'Fail', or 'No Status')
    
    Returns:
        Tuple[bool, str, Optional[Dict]]: (success, message, history)
    """
    if new_state not in ['Pass', 'Fail', 'No Status']:
        return False, "Invalid state. Must be 'Pass', 'Fail', or 'No Status'", None
    
    conn = get_db_connection()
    try:
        # Get current state and history
        current = conn.execute('''
            SELECT state, last_failure, history_count, type 
            FROM diagnostic_codes 
            WHERE code = ? AND enabled = 1
        ''', (code,)).fetchone()
        
        if not current:
            return False, f"Code {code} not found or not enabled", None
        
        # Prepare update data
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_data = {
            'state': new_state,
            'last_failure': current_time if new_state in ['Fail', 'No Status'] else current['last_failure'],
            'history_count': current['history_count'] + 1 if new_state in ['Fail', 'No Status'] else current['history_count']
        }
        
        # Update the record
        conn.execute('''
            UPDATE diagnostic_codes 
            SET state = ?,
                last_failure = ?,
                history_count = ?
            WHERE code = ? AND enabled = 1
        ''', (update_data['state'], update_data['last_failure'], 
              update_data['history_count'], code))
        
        conn.commit()
        
        # Get updated record
        updated = conn.execute('''
            SELECT state, last_failure, history_count, type 
            FROM diagnostic_codes 
            WHERE code = ? AND enabled = 1
        ''', (code,)).fetchone()
        
        return True, "Update successful", {
            'code': code,
            'state': updated['state'],
            'last_failure': updated['last_failure'],
            'history_count': updated['history_count'],
            'type': updated['type']
        }
        
    except Exception as e:
        return False, f"Error updating diagnostic: {str(e)}", None
    finally:
        conn.close()

def update_diagnostics_batch(updates: List[Dict[str, str]]) -> Tuple[List[Dict], List[str]]:
    """
    Update multiple diagnostic codes in a single batch and send one alert for all updates.
    
    Args:
        updates (List[Dict[str, str]]): List of dictionaries with 'code' and 'state' keys
            Example: [{'code': 'H001', 'state': 'Fail'}, {'code': 'T001', 'state': 'Pass'}]
    
    Returns:
        Tuple[List[Dict], List[str]]: (successful_updates, error_messages)
    """
    successful_updates = []
    error_messages = []
    alert_updates = []
    
    # First, perform all updates
    for update in updates:
        success, message, history = update_diagnostic(update['code'], update['state'])
        if success:
            successful_updates.append(history)
            if history['state'] in ['Fail', 'No Status']:
                alert_updates.append(history)
        else:
            error_messages.append(f"Code {update['code']}: {message}")
    
    # Then, send a single alert for all failed/no-status updates
    if alert_updates:
        send_diagnostic_alert(alert_updates)
    
    return successful_updates, error_messages

def print_diagnostics(diagnostics: Optional[List[Dict]] = None) -> None:
    """
    Print diagnostic information in a formatted way.
    Only shows diagnostics with 'Fail' or 'No Status' states.
    
    Args:
        diagnostics (Optional[List[Dict]]): List of diagnostic information to print.
            If None, fetches current enabled diagnostics.
    """
    if diagnostics is None:
        diagnostics = get_enabled_diagnostics()
    
    # Filter for only Fail and No Status
    diagnostics = [d for d in diagnostics if d['state'] in ['Fail', 'No Status']]
    
    if not diagnostics:
        print("No failed or no-status diagnostics found.")
        return
    
    # Group by type
    by_type = {}
    for d in diagnostics:
        if d['type'] not in by_type:
            by_type[d['type']] = []
        by_type[d['type']].append(d)
    
    # Print each type
    for dtype, codes in by_type.items():
        print(f"\n{dtype} Diagnostics:")
        print("-" * 80)
        print(f"{'Code':<10} {'State':<12} {'Last Failure':<25} {'History Count':<15}")
        print("-" * 80)
        
        for code in codes:
            state_color = {
                'Fail': '\033[91m',  # Red
                'No Status': '\033[93m'  # Yellow
            }.get(code['state'], '')
            
            print(f"{code['code']:<10} {state_color}{code['state']:<12}\033[0m "
                  f"{code['last_failure'] or 'N/A':<25} {code['history_count']:<15}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("1. View current diagnostics:")
        print("   python update_diagnostic.py view")
        print("2. Update multiple diagnostics:")
        print("   python update_diagnostic.py batch <code1> <state1> <code2> <state2> ...")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'view':
        print_diagnostics()
    
    elif command == 'batch':
        if len(sys.argv) < 4 or len(sys.argv) % 2 != 0:
            print("Usage: python update_diagnostic.py batch <code1> <state1> <code2> <state2> ...")
            sys.exit(1)
        
        updates = []
        for i in range(2, len(sys.argv), 2):
            updates.append({
                'code': sys.argv[i],
                'state': sys.argv[i + 1]
            })
        
        successful, errors = update_diagnostics_batch(updates)
        
        if successful:
            print("\nSuccessfully updated diagnostics:")
            print_diagnostics(successful)
        
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"- {error}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main() 