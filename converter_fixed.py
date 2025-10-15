"""
Fixed MultiPolygon to GeoJSON Converter for Mapbox 3D Visualization

Handles common geometry issues:
- Duplicate coordinates
- 3D coordinates in 2D polygons  
- Invalid geometries
- Precision issues

Usage:
    python converter_fixed.py
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.validation import explain_validity
import warnings
warnings.filterwarnings('ignore')


def clean_coordinates(coords):
    """
    Clean coordinate list by removing duplicates and ensuring minimum 3 points.
    """
    if len(coords) < 3:
        return None
    
    # Remove duplicate consecutive coordinates
    cleaned = []
    prev_coord = None
    for coord in coords:
        # Handle 3D coordinates by taking only X,Y
        if len(coord) >= 2:
            x, y = coord[0], coord[1]
            current_coord = (x, y)
            
            # Skip if same as previous coordinate
            if prev_coord is None or current_coord != prev_coord:
                cleaned.append(current_coord)
                prev_coord = current_coord
    
    # Ensure we have at least 3 points and it's closed
    if len(cleaned) < 3:
        return None
    
    # Close the polygon if not already closed
    if cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])
    
    return cleaned


def fix_polygon(polygon):
    """
    Attempt to fix invalid polygon geometry.
    """
    if polygon.is_valid:
        return polygon
    
    # Try buffer(0) to fix self-intersections
    try:
        fixed = polygon.buffer(0)
        if fixed.is_valid and fixed.area > 0:
            return fixed
    except:
        pass
    
    # Try to reconstruct from cleaned coordinates
    try:
        coords = clean_coordinates(list(polygon.exterior.coords))
        if coords and len(coords) >= 4:  # At least 3 points + closing point
            new_poly = Polygon(coords)
            if new_poly.is_valid and new_poly.area > 0:
                return new_poly
    except:
        pass
    
    return None


def process_multipolygon_file(filepath, height_field=None):
    """
    Process a MultiPolygon shapefile with improved geometry handling.
    """
    print(f"Processing: {os.path.basename(filepath)}")
    
    try:
        # Read the shapefile
        gdf = gpd.read_file(filepath)
        print(f"  - Found {len(gdf)} features")
        print(f"  - Geometry type: {gdf.geometry.geom_type.unique()}")
        
        # Get CRS
        crs = gdf.crs
        print(f"  - CRS: {crs}")
        
        # Convert timestamp columns to strings
        for col in gdf.columns:
            if gdf[col].dtype == 'datetime64[ns]' or 'datetime' in str(gdf[col].dtype):
                print(f"  - Converting timestamp column '{col}' to string")
                gdf[col] = gdf[col].astype(str)
        
        feature_list = []
        
        # Process each feature
        for idx, row in gdf.iterrows():
            properties = row.drop('geometry').to_dict()
            geometry = row.geometry
            
            # Calculate building height from elevation difference
            if 'ROOFTOP__2' in properties and 'GRD_ELEV_2' in properties:
                rooftop_elev = float(properties['ROOFTOP__2'])
                ground_elev = float(properties['GRD_ELEV_2'])
                height = max(0, rooftop_elev - ground_elev)
                if idx < 5:  # Only print first 5 for debugging
                    print(f"  - Building {idx+1}: {height:.2f}m (rooftop: {rooftop_elev:.2f}m - ground: {ground_elev:.2f}m)")
            else:
                height = 10.0  # Default height
                print(f"  - Building {idx+1}: Using default height {height}m")
            
            # Handle MultiPolygon geometry
            if geometry.geom_type == 'MultiPolygon':
                valid_polygons = []
                invalid_polygons = []
                
                # Process each polygon in the MultiPolygon
                polygons_list = list(geometry.geoms) if hasattr(geometry, 'geoms') else [geometry]
                for poly_idx, polygon in enumerate(polygons_list):
                    # Try to fix the polygon
                    fixed_poly = fix_polygon(polygon)
                    
                    if fixed_poly is not None and fixed_poly.area > 0:
                        valid_polygons.append(fixed_poly)
                    else:
                        invalid_polygons.append(polygon)
                
                print(f"  - Building {idx+1}: {len(valid_polygons)} valid, {len(invalid_polygons)} invalid polygons")
                
                # Create features for valid polygons
                for poly_idx, polygon in enumerate(valid_polygons):
                    new_properties = properties.copy()
                    new_properties['height'] = height
                    new_properties['polygon_id'] = poly_idx
                    new_properties['feature_id'] = idx
                    
                    feature_list.append({
                        'type': 'Feature',
                        'properties': new_properties,
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [list(polygon.exterior.coords)]
                        }
                    })
            
            elif geometry.geom_type == 'Polygon':
                fixed_poly = fix_polygon(geometry)
                if fixed_poly is not None and fixed_poly.area > 0:
                    new_properties = properties.copy()
                    new_properties['height'] = height
                    new_properties['feature_id'] = idx
                    
                    feature_list.append({
                        'type': 'Feature',
                        'properties': new_properties,
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [list(fixed_poly.exterior.coords)]
                        }
                    })
        
        print(f"  - Extracted {len(feature_list)} building polygons")
        return feature_list, crs
        
    except Exception as e:
        print(f"  - Error processing file: {e}")
        return [], None


def main():
    """Main function to process all MultiPolygon files and create GeoJSON output."""
    
    # Input and output directories
    input_dir = "data/input"
    output_dir = "data/output"
    output_file = os.path.join(output_dir, "buildings.geojson")
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist!")
        return
    
    # Find all shapefiles in input directory
    shapefiles = glob.glob(os.path.join(input_dir, "*.shp"))
    
    if not shapefiles:
        print(f"No .shp files found in '{input_dir}'")
        return
    
    print(f"Found {len(shapefiles)} shapefile(s) to process:")
    for shp in shapefiles:
        print(f"  - {os.path.basename(shp)}")
    
    # Process all files
    all_features = []
    output_crs = None
    
    for shapefile in shapefiles:
        features, crs = process_multipolygon_file(shapefile)
        all_features.extend(features)
        
        if output_crs is None and crs is not None:
            output_crs = crs
    
    if not all_features:
        print("No valid building features found!")
        return
    
    print(f"\nTotal buildings extracted: {len(all_features)}")
    
    # Create GeoDataFrame from all features
    gdf = gpd.GeoDataFrame.from_features(all_features, crs=output_crs)
    
    # Convert to WGS84 (EPSG:4326) for Mapbox compatibility
    print("Converting to WGS84 (EPSG:4326) for web mapping...")
    gdf = gdf.to_crs('EPSG:4326')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as GeoJSON
    print(f"Saving to: {output_file}")
    gdf.to_file(output_file, driver='GeoJSON')
    
    # Print summary statistics
    heights = [f['properties']['height'] for f in all_features]
    print(f"\nBuilding Height Statistics:")
    print(f"  - Count: {len(heights)}")
    print(f"  - Min height: {min(heights):.2f} m")
    print(f"  - Max height: {max(heights):.2f} m")
    print(f"  - Average height: {sum(heights)/len(heights):.2f} m")
    
    print(f"\nConversion complete! GeoJSON saved to: {output_file}")
    print("You can now open index.html in your browser to visualize the 3D buildings.")


if __name__ == "__main__":
    main()
