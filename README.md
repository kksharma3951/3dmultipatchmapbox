# 3D Multipatch Mapbox Showcase

A simple proof-of-concept application that converts ESRI Multipatch building geometries to GeoJSON and displays them as 3D extruded buildings in Mapbox GL JS.

## Overview

This project demonstrates how to:
- Convert ESRI Multipatch shapefiles to GeoJSON with height attributes
- Visualize 3D buildings in a web browser using Mapbox GL JS
- Process multiple multipatch files in batch

Based on the [bbonczak/multipatch_convertor](https://github.com/bbonczak/multipatch_convertor) library.

## Quick Start

### 1. Setup

```bash
# Clone or download this project
cd 3dmultipatchmapbox

# Create and activate virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Prepare Your Data

1. Place your 2-3 ESRI Multipatch shapefiles (`.shp`, `.shx`, `.dbf`, `.prj`) in the `data/input/` directory
2. Make sure the shapefiles contain multipatch geometries with Z-coordinates

### 3. Convert to GeoJSON

```bash
python converter.py
```

This will:
- Process all `.shp` files in `data/input/`
- Extract building footprints and heights from multipatch geometries
- Output a single `buildings.geojson` file to `data/output/`

### 4. Visualize in Browser

1. **Get a Mapbox access token:**
   - Sign up at [mapbox.com](https://www.mapbox.com/) (free tier available)
   - Go to [Access Tokens](https://account.mapbox.com/access-tokens/)
   - Copy your default public token

2. **Update the token in `index.html`:**
   ```javascript
   // Replace this line in index.html:
   mapboxgl.accessToken = 'pk.eyJ1IjoieW91ci11c2VybmFtZSIsImEiOiJjbGV4YW1wbGUifQ.YOUR_ACCESS_TOKEN_HERE';
   
   // With your actual token:
   mapboxgl.accessToken = 'pk.eyJ1IjoieW91ci11c2VybmFtZSIsImEiOiJjbGV4YW1wbGUifQ.YOUR_ACTUAL_TOKEN_HERE';
   ```

3. **Open the visualization:**
   - **Option A:** Double-click `index.html` (may need a web server for CORS)
   - **Option B:** Run a simple web server:
     ```bash
     python -m http.server 8000
     ```
     Then open: http://localhost:8000

## Project Structure

```
3dmultipatchmapbox/
├── data/
│   ├── input/          # Place your multipatch .shp files here
│   └── output/         # Converted buildings.geojson appears here
├── converter.py        # Python script to convert multipatch → GeoJSON
├── index.html          # Mapbox GL JS 3D visualization
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Features

### Conversion Script (`converter.py`)
- **Batch Processing:** Handles multiple shapefiles automatically
- **Height Extraction:** Calculates building heights from Z-coordinates
- **Coordinate System:** Converts to WGS84 (EPSG:4326) for web compatibility
- **Validation:** Filters out invalid geometries and very small buildings
- **Statistics:** Reports building count, height ranges, and averages

### 3D Visualization (`index.html`)
- **Interactive 3D View:** Rotate, zoom, and tilt to explore buildings
- **Height-based Coloring:** Buildings colored by height (blue → gray)
- **Click Information:** Click buildings to see height and ID details
- **Manual Controls:** Adjust pitch, bearing, and height scale
- **Statistics Display:** Shows building count and height statistics
- **Responsive Design:** Works on desktop and mobile devices

## Usage Tips

### For the Conversion Script
- **Input Requirements:** Shapefiles must contain multipatch geometries with Z-coordinates
- **Height Units:** Supports meters and feet (automatically detected)
- **Coordinate Systems:** Any input CRS supported (outputs WGS84)
- **Performance:** Optimized for small datasets (2-3 buildings), may be slow for large datasets

### For the Visualization
- **Navigation:** 
  - Left-click + drag to rotate
  - Right-click + drag to tilt
  - Scroll to zoom
- **Controls:**
  - Adjust pitch (tilt angle) from 0° to 85°
  - Set bearing (rotation) from 0° to 360°
  - Scale building heights from 0.1x to 3.0x
- **Browser Compatibility:** Works in Chrome, Firefox, Safari, Edge

## Troubleshooting

### Common Issues

1. **"No .shp files found"**
   - Ensure your shapefiles are in `data/input/`
   - Check that all shapefile components are present (.shp, .shx, .dbf, .prj)

2. **"No valid building features found"**
   - Verify shapefiles contain multipatch geometries
   - Check that Z-coordinates are present and valid
   - Try reducing the minimum height threshold in `converter.py`

3. **"Failed to load buildings.geojson"**
   - Run `python converter.py` first to generate the GeoJSON
   - Check that `data/output/buildings.geojson` exists
   - Use a web server if opening HTML directly fails

4. **"Mapbox Token Required" error**
   - Replace the placeholder token in `index.html` with your actual Mapbox token
   - Ensure the token has the correct permissions

5. **Buildings don't appear in 3D**
   - Check browser console for JavaScript errors
   - Verify the GeoJSON has valid height properties
   - Try adjusting the height scale control

### Performance Notes
- This is designed for **small datasets** (2-3 buildings)
- For larger datasets, consider using Mapbox Studio or server-side processing
- Browser performance may vary with complex geometries

## Dependencies

### Python
- `geopandas` - Geospatial data processing
- `shapely` - Geometric operations
- `fiona` - Shapefile I/O
- `pyproj` - Coordinate transformations

### Web
- `Mapbox GL JS` - 3D mapping library (loaded via CDN)
- Modern web browser with WebGL support

## License

This project is based on the MIT-licensed [multipatch_convertor](https://github.com/bbonczak/multipatch_convertor) library.

## References

- [ESRI Multipatch Documentation](https://support.esri.com/en/white-paper/1483)
- [Mapbox GL JS Documentation](https://docs.mapbox.com/mapbox-gl-js/)
- [NYC Energy & Water Performance Map](https://energy.cusp.nyu.edu/) - Example usage of similar technology
- [GeoPandas Documentation](https://geopandas.org/)

## Support

For issues with:
- **Multipatch conversion:** Check the original [multipatch_convertor](https://github.com/bbonczak/multipatch_convertor) repository
- **Mapbox visualization:** See [Mapbox GL JS documentation](https://docs.mapbox.com/mapbox-gl-js/)
- **This project:** Open an issue in this repository
