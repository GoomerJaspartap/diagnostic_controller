# Room-Specific Slope Configurations

This update adds support for room-specific slope configurations, allowing you to define different temperature and humidity slope behaviors for different rooms or locations in your facility.

## 🆕 New Features

### Room-Based Slope Configurations
- **Room-Specific Settings**: Each room can now have its own slope configurations
- **General Configurations**: Fallback configurations that apply to all rooms when no room-specific config exists
- **Smart Fallback**: The system automatically uses room-specific configs first, then falls back to general configs

### Enhanced Slope Calculation
- **Room-Aware Calculations**: Slope calculations now consider the room where the diagnostic code is located
- **Priority System**: Room-specific configurations take priority over general ones
- **Seamless Integration**: Existing functionality continues to work with new room-aware features

## 🏗️ Database Changes

The following tables have been updated to support room-specific configurations:

### `slope_configurations` Table
- Added `room_id` column (INTEGER, references rooms.id)
- `room_id = NULL` means the configuration applies to all rooms (general)
- `room_id = <room_id>` means the configuration applies only to that specific room

### `humidity_slope_configurations` Table
- Added `room_id` column (INTEGER, references rooms.id)
- Same room-specific behavior as temperature configurations

## 🚀 How to Use

### 1. Create Room-Specific Configurations

When adding or editing slope configurations, you can now:

1. **Select a Room**: Choose a specific room from the dropdown
2. **Leave as General**: Select "General (All Rooms)" for configurations that apply everywhere
3. **Room-Specific Overrides**: Create different slope values for different rooms

### 2. Configuration Priority

The system follows this priority order:

1. **Room-Specific Config**: If a diagnostic code is in Room A, use Room A's slope configs
2. **General Config**: If no room-specific config exists, fall back to general configs
3. **No Config**: If neither exists, the slope calculation will fail gracefully

### 3. Example Use Cases

#### Different Room Characteristics
- **Server Room**: Fast temperature changes (high slopes) due to high heat generation
- **Office Space**: Moderate temperature changes (medium slopes) for comfort
- **Storage Area**: Slow temperature changes (low slopes) for stability

#### Seasonal Variations by Room
- **North-Facing Rooms**: Different winter slopes due to sun exposure
- **Basement Rooms**: Different humidity slopes due to moisture levels
- **Roof-Top Units**: Different summer slopes due to direct sun exposure

## 🔧 Migration

### For Existing Installations

1. **Run the Migration Script**:
   ```bash
   python migrate_room_slopes.py
   ```

2. **Verify Migration**:
   - Check that existing configurations now show "General" as their room
   - Confirm no data was lost during migration

3. **Start Using Room-Specific Features**:
   - Edit existing configurations to assign them to specific rooms
   - Create new room-specific configurations as needed

### Migration Script Details

The migration script will:
- Add `room_id` columns to both slope configuration tables
- Set all existing configurations to `room_id = NULL` (general)
- Preserve all existing slope values and settings
- Provide a summary of the migration results

## 📊 Benefits

### Better Accuracy
- **Room-Specific Behavior**: More accurate slope calculations for each location
- **Environmental Factors**: Consider room-specific conditions (sun exposure, ventilation, etc.)
- **Usage Patterns**: Different rooms may have different operational requirements

### Improved Management
- **Organized Configurations**: Group slope configs by room for easier management
- **Flexible Overrides**: Room-specific settings without affecting other areas
- **Better Documentation**: Clear understanding of which configs apply where

### Enhanced Diagnostics
- **Precise Calculations**: More accurate time-to-achieve estimates
- **Room-Aware Alerts**: Better understanding of room-specific performance
- **Targeted Optimization**: Optimize slopes for specific room conditions

## 🎯 Best Practices

### 1. Start with General Configurations
- Create general slope configurations as baseline settings
- Use these for rooms with similar characteristics

### 2. Add Room-Specific Overrides
- Identify rooms with unique characteristics
- Create room-specific configurations for those rooms
- Keep general configs for standard rooms

### 3. Regular Review
- Periodically review room-specific configurations
- Update slopes based on seasonal performance data
- Remove unused room-specific configs to avoid confusion

### 4. Documentation
- Document why specific rooms have different slopes
- Note environmental factors that influence room behavior
- Keep track of configuration changes and their impact

## 🔍 Troubleshooting

### Common Issues

1. **Slope Calculation Fails**:
   - Check if room has slope configurations
   - Verify general configurations exist as fallback
   - Ensure diagnostic codes are assigned to valid rooms

2. **Unexpected Slope Behavior**:
   - Verify room assignment for diagnostic codes
   - Check for conflicting room-specific vs. general configs
   - Review slope value ranges for overlaps

3. **Migration Issues**:
   - Ensure database user has ALTER TABLE permissions
   - Check for existing room_id columns
   - Verify rooms table exists and has data

### Debug Information

The slope calculation now provides enhanced debugging:
- Shows which configurations were used
- Indicates whether room-specific or general configs were applied
- Provides fallback information when room-specific configs aren't found

## 📈 Future Enhancements

Potential future improvements:
- **Room Groups**: Apply configurations to groups of similar rooms
- **Time-Based Configs**: Different slopes for different times of day
- **Conditional Configs**: Dynamic slope selection based on room conditions
- **Performance Analytics**: Track how well room-specific configs perform

## 🤝 Support

If you encounter issues or have questions:
1. Check the troubleshooting section above
2. Review the migration script output
3. Verify database schema changes were applied correctly
4. Check application logs for detailed error messages

---

**Note**: This feature maintains backward compatibility. Existing slope configurations will continue to work and will be treated as general configurations after migration.



