import pandas as pd
import numpy as np

# List of file paths in the exact order you want them combined
input_files = [
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-15-001.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-16-001.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-16-002.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-16-003.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-17-001.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-18-001.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-19-001.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-20-001.csv",
    "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-21-001.csv",
]
dfs = []
# Collect all unique column names across all files
all_columns = set()
# Read each file and collect columns
for file in input_files:
    try:
        df = pd.read_csv(file)
        # Ensure Elapsed Time is numeric for consistency
        df["Elapsed Time"] = pd.to_numeric(df["Elapsed Time"], errors="coerce")
        dfs.append(df)
        all_columns.update(df.columns)
    except FileNotFoundError:
        print(f"File {file} not found. Skipping...")
        continue
    except Exception as e:
        print(f"Error reading {file}: {e}. Skipping...")
        continue
# Check if any files were successfully loaded
if not dfs:
    print("No valid CSV files found.")
    exit()
# Use the column order from the first file as the reference
if dfs:
    reference_columns = dfs[0].columns.tolist()
    # Add any additional columns from other files (not present in the first file)
    additional_columns = [col for col in all_columns if col not in reference_columns]
    final_columns = reference_columns + additional_columns
else:
    final_columns = sorted(list(all_columns))  # Fallback, though unlikely
# Initialize an empty list to store aligned DataFrames
aligned_dfs = []

# Align each DataFrame to have all columns, preserving Elapsed Time and Time
for df in dfs:
    # Create a new DataFrame with all columns in the reference order
    aligned_df = pd.DataFrame(columns=final_columns)
    # Copy existing columns from the current DataFrame
    for col in df.columns:
        aligned_df[col] = df[col]
    # Fill missing columns with empty strings
    for col in final_columns:
        if col not in df.columns:
            aligned_df[col] = ""
    aligned_dfs.append(aligned_df)


combined_df = pd.concat(aligned_dfs, ignore_index=True)


numeric_columns = [col for col in final_columns if col not in ["Time"]]
for col in numeric_columns:
    combined_df[col] = pd.to_numeric(combined_df[col], errors="coerce").fillna("")

combined_df["Time"] = combined_df["Time"].astype(str)

# Save the combined data to a new CSV file
output_file = "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/combined_aggregated_data.csv"
combined_df.to_csv(output_file, index=False)
print(f"Combined data saved to {output_file}")