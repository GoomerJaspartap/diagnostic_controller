# CSV Import/Export for Slope Configurations

This feature allows you to easily manage slope configurations by importing and exporting them as CSV files. This is especially useful for:

- **Bulk configuration updates** - Update multiple configurations at once
- **Offline editing** - Download, edit in Excel/Google Sheets, then re-upload
- **Backup and restore** - Export current configs, make changes, then import
- **Template sharing** - Share configuration templates with team members

## How to Use

### 1. Export Current Configurations

1. Go to **Configurations** page
2. Click **"Export Current Configs"** button
3. This downloads a CSV file with all your current slope configurations

### 2. Download Template

1. Click **"Download Template"** button
2. This gives you a CSV template with example data
3. Use this as a starting point for new configurations

### 3. Import CSV

1. Prepare your CSV file (see format below)
2. Click **"Choose File"** and select your CSV
3. Click **"Import"** button
4. The system will validate and import your configurations

## CSV Format

The CSV must have exactly 10 columns in this order:

| Column | Description | Example |
|--------|-------------|---------|
| Configuration Type | Must be "Temperature" or "Humidity" | `Temperature` |
| Room Name | Room name or "General" for no specific room | `Room A` |
| Min Value | Minimum temperature/humidity value | `18.0` |
| Max Value | Maximum temperature/humidity value | `25.0` |
| Summer Positive Slope | Summer positive slope value | `0.5` |
| Summer Negative Slope | Summer negative slope value | `-0.3` |
| Fall Positive Slope | Fall positive slope value | `0.4` |
| Fall Negative Slope | Fall negative slope value | `-0.2` |
| Winter Positive Slope | Winter positive slope value | `0.6` |
| Winter Negative Slope | Winter negative slope value | `-0.4` |

## Example CSV Content

```csv
Configuration Type,Room Name,Min Value,Max Value,Summer Positive Slope,Summer Negative Slope,Fall Positive Slope,Fall Negative Slope,Winter Positive Slope,Winter Negative Slope
Temperature,Room A,18.0,25.0,0.5,-0.3,0.4,-0.2,0.6,-0.4
Temperature,Room B,20.0,28.0,0.6,-0.4,0.5,-0.3,0.7,-0.5
Humidity,General,30.0,70.0,2.0,-1.5,1.8,-1.3,2.2,-1.7
```

## Important Notes

### Room Names
- **Specific Room**: Use the exact room name as it appears in your system
- **General**: Use "General" (or leave blank) for configurations that apply to all rooms
- **Case Sensitive**: Room names are case-sensitive

### Validation Rules
- Min value must be less than max value
- No overlapping ranges for the same room and configuration type
- All numeric values must be valid numbers
- Configuration type must be exactly "Temperature" or "Humidity"

### Error Handling
- If any row fails validation, it will be skipped
- Success and error counts are shown after import
- First 10 errors are displayed in detail
- The import continues even if some rows fail

## Workflow Examples

### Scenario 1: Bulk Update
1. Export current configurations
2. Edit values in Excel/Google Sheets
3. Import the updated CSV
4. All configurations are updated at once

### Scenario 2: New Setup
1. Download template
2. Fill in your configuration values
3. Import the CSV
4. All configurations are created

### Scenario 3: Room Addition
1. Export current configurations
2. Add new rows for the new room
3. Import the updated CSV
4. New room configurations are added

## Troubleshooting

### Common Issues

**"Room not found" error**
- Check that room names match exactly (including case)
- Use "General" for room-independent configurations

**"Overlapping ranges" error**
- Ensure temperature/humidity ranges don't overlap for the same room
- Check existing configurations first

**"Invalid numeric value" error**
- Ensure all numeric fields contain valid numbers
- Check for extra spaces or special characters

**"Insufficient columns" error**
- Ensure your CSV has exactly 10 columns
- Check for missing commas or extra columns

### Tips for Success

1. **Always use the template** as a starting point
2. **Test with a small file** first
3. **Backup your current configurations** before bulk imports
4. **Use Excel/Google Sheets** for easier editing
5. **Validate room names** before importing

## File Requirements

- **Format**: CSV (Comma Separated Values)
- **Encoding**: UTF-8
- **Headers**: Required (first row)
- **Delimiter**: Comma (,)
- **File Extension**: .csv

## Security

- Only authenticated users can import/export
- Files are processed server-side
- No files are permanently stored
- All data is validated before database insertion



