from update_diagnostic import update_diagnostics_batch, print_diagnostics

# Batch update
updates = [
    {'code': 'T001', 'state': 'Fail'},
     {'code': 'T002', 'state': 'Fail'} 
]
successful, errors = update_diagnostics_batch(updates)
