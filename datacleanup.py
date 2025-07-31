import pandas as pd
import numpy as np
# File paths
input_file = "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/2025-07-17-001.xlsx"  # Replace with your actual input file path
output_file = "/Users/jaspartapgoomer/Downloads/DR files for Jas - Kelvin  15JL to 21JL/Aggregated/2025-07-17-001.csv"  # Output file path
df = pd.read_excel(input_file, sheet_name="10 Samples")

df["Elapsed Time"] = pd.to_numeric(df["Elapsed Time"], errors="coerce")
df = df.dropna(subset=["Elapsed Time"])
minute_marks = df[df["Elapsed Time"] % 60 == 0]

columns_to_average = [col for col in df.columns if col not in ["Sample No", "Elapsed Time", "Time"]]
aggregated_data = []

# Iterate over each minute mark
for idx, minute_row in minute_marks.iterrows():
    sample_no = minute_row["Sample No"]
    elapsed_time = minute_row["Elapsed Time"]
    start_sample = sample_no - 6 if sample_no > 6 else 1
    end_sample = sample_no

    sample_range = df[(df["Sample No"] >= start_sample) & (df["Sample No"] <= end_sample)]
    if not sample_range.empty:
        new_row = {"Sample No": sample_no, "Elapsed Time": elapsed_time, "Time": minute_row["Time"]}
        # Compute the mean for other columns and round to 2 decimal places
        for col in columns_to_average:
            new_row[col] = round(sample_range[col].mean(), 2)
        aggregated_data.append(new_row)
result = pd.DataFrame(aggregated_data)
result = result[df.columns]
# Save the aggregated data to a new CSV file
result.to_csv(output_file, index=False)
print(f"Aggregated data saved to {output_file}")