import pandas as pd
import plotly.graph_objs as go
from plotly.offline import plot

def plot_excel_graph(
    file_path: str,
    sheet_name: str,
    skip_rows: list[int] = []
):
    # Read the Excel file
    df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skip_rows)

    # Drop completely empty rows
    df.dropna(how='all', inplace=True)

    print("\nAvailable columns:")
    for idx, col in enumerate(df.columns):
        print(f"{idx}: {col}")

    # Ask for X and Y axis selections
    x_index = int(input("\nEnter the number for the X-axis column: "))
    y_indices = input("Enter one or more Y-axis column numbers (comma-separated): ")

    x_col = df.columns[x_index]
    y_cols = [df.columns[int(i.strip())] for i in y_indices.split(",")]

    print(f"\nPlotting {', '.join(y_cols)} vs {x_col}...")

    # Create the plot
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
    output_file = "interactive_plot.html"
    plot(fig, filename=output_file, auto_open=True)
    print(f"\n✅ Plot saved as '{output_file}'")

# Example usage
if __name__ == "__main__":
    print("📊 Excel to HTML Graph Generator")
    file_path = input("Enter Excel file path (e.g., data.xlsx): ").strip()
    sheet_name = input("Enter sheet name (default is 'Sheet1'): ").strip() or "Sheet1"
    skip_input = input("Enter line numbers to skip (comma-separated), or leave blank: ").strip()

    if skip_input:
        skip_lines = [int(i.strip()) for i in skip_input.split(",")]
    else:
        skip_lines = []

    plot_excel_graph(file_path, sheet_name, skip_lines)
