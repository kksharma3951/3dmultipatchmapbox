# 3D Multipatch Mapbox - Project Context

## Current Status: WORKING ✅

The visualization is now working correctly with proper building heights and multi-level roof details preserved.

### New Feature: Floor Separation Lines (multifloor branch)
- Added horizontal floor separation lines at 3m intervals
- Buildings now show clear visual floor divisions
- Clean beige/tan color scheme for buildings with charcoal gray floor lines
- Generates 40,877 floor lines for 2,867 buildings (avg 46.3m height)

## The Fix (Completed)

**Root Cause:** We weren't passing `relative_h=True` to `process_multipatch_file()` on line 159 of converter.py.

**Solution Implemented:**
- Added `relative_h=True` parameter to convert absolute elevations to relative heights
- Updated HTML to properly use `base_height` and `top_height` fields
- Result: Beautiful multi-level roof structures with realistic heights (average ~38m)

**Current Visualization:**
- 26,091 buildings displayed
- Average height: 38.3m (realistic for downtown buildings)
- Multi-level roof complexity preserved
- Buildings look correct and proportional

## Repository Cleanup (Completed)

**Removed:**
- `feature/multi-level-heights` branch (both local and remote)
- All experimental converter files:
  - converter_adjusted.py
  - converter_attributes.py
  - converter_correct.py
  - converter_fixed.py
  - converter_multipolygon.py
  - converter_original.py
  - converter_original_relative.py
  - converter_simple.py
  - original_multipatch_convertor.py
- Debug files: debug.html, debug_data.py, nul

**Current Clean Structure:**
```
3dmultipatchmapbox/
├── .claude/
│   └── CLAUDE.md (this file)
├── data/
│   ├── input/  (multipatch shapefiles)
│   └── output/ (buildings.geojson)
├── converter.py (working converter)
├── index.html (working visualization)
├── requirements.txt
├── README.md
└── venv/
```

## Next Steps: Full Stack Development

### Phase 1: Streamlit POC
Create a Python-based proof of concept with Streamlit:
- File upload interface for multipatch shapefiles
- Real-time conversion and visualization
- Interactive parameter adjustment
- Export capabilities

### Phase 2: CABINS Integration
Integrate the multipatch visualization into the CABINS full-stack app:
- Backend API for multipatch processing
- Frontend 3D visualization component
- Database integration for building data
- User management and project organization

## Technical Details

### Working Converter Logic
```python
# Line 159 in converter.py
features, crs = process_multipatch_file(shapefile, relative_h=True)
```

### Data Structure
- Each multipatch building is exploded into individual polygon parts
- Each part has: min_z, max_z, height, base_height, top_height
- Heights are relative to ground elevation (GRD_ELEV_2 field)

### Visualization Stack
- **Backend:** Python + geopandas + shapely
- **Frontend:** Mapbox GL JS with fill-extrusion layer
- **Data Format:** GeoJSON with 3D properties

### Floor Separation Lines Implementation
- **Function:** `generateFloorLines()` in index.html
- Creates thin horizontal bands (15cm thick) at each floor level
- Uses `fill-extrusion-base` and `fill-extrusion-height` for positioning
- Default floor height: 3.0 meters
- Color scheme: Buildings (#D4C5B0 beige), Floor lines (#3d3d3d charcoal)

## Key Insights Learned

1. **Absolute vs Relative Heights:**
   - Multipatch data contains absolute elevations (~1046-1289m)
   - Web visualization needs relative heights from ground
   - The `relative_h=True` parameter handles this conversion

2. **Multi-level Structures:**
   - Multipatch contains beautiful 3D roof detail
   - Each building can have multiple polygon parts at different heights
   - Preserving this detail requires proper base_height and top_height

3. **Reference Code:**
   - bbonczak's multipatch_convertor was the key reference
   - Original implementation had the solution all along
   - Sometimes the simple solution is the right one

## Development Notes

**Server for Testing:**
```bash
python -m http.server 8000
# Open: http://localhost:8000
```

**Branches:**
- `main`: Stable working version with basic 3D building visualization
- `multifloor`: Floor separation lines feature (in progress)

**Current Branch:** multifloor

**Last Updated:** 2025-11-09
