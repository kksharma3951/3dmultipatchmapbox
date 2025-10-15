"""
MultiPolygon to GeoJSON Converter for Mapbox 3D Visualization

Specifically designed for MultiPolygon shapefiles with height attributes
(not MultiPatch geometries). This is more appropriate for your Calgary building data.

Usage:
    python converter_multipolygon.py
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon
import warnings
warnings.filterwarnings('ignore')


def process_multipolygon_file(filepath, height_field=None):
    """
    Process a MultiPolygon shapefile with height attributes.
    
    Args:
        filepath: Path to the shapefile
        height_field: Name of height attribute (auto-detected if None)
    
    Returns:
        List of GeoJSON features with height attributes
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
        
        # Convert timestamp columns to strings to avoid JSON serialization errors
        for col in gdf.columns:
            if gdf[col].dtype == 'datetime64[ns]' or 'datetime' in str(gdf[col].dtype):
                print(f"  - Converting timestamp column '{col}' to string")
                gdf[col] = gdf[col].astype(str)
        
        feature_list = []
        
        # Process each feature
        for idx, row in gdf.iterrows():
            properties = row.drop('geometry').to_dict()
            geometry = row.geometry
            
            # Auto-detect height field if not specified
            if height_field is None:
                # Look for common height field names, prioritizing rooftop heights
                height_candidates = [col for col in gdf.columns if 
                                   any(keyword in col.upper() for keyword in 
                                       ['ROOFTOP__2', 'ROOFTOP_EL', 'HEIGHT', 'ELEV', 'Z', 'ROOFTOP', 'TOWER'])]
                
                if height_candidates:
                    # Use the first height-related field
                    height_field = height_candidates[0]
                    print(f"  - Auto-detected height field: {height_field}")
                else:
                    print("  - Warning: No height field detected, using default height of 10m")
                    height_field = 'DEFAULT_HEIGHT'
                    properties[height_field] = 10.0
            
            # Calculate building height from elevation difference
            if 'ROOFTOP__2' in properties and 'GRD_ELEV_2' in properties:
                # Use rooftop elevation minus ground elevation
                rooftop_elev = float(properties['ROOFTOP__2'])
                ground_elev = float(properties['GRD_ELEV_2'])
                height = max(0, rooftop_elev - ground_elev)  # Ensure positive height
                print(f"  - Building height: {height:.2f}m (rooftop: {rooftop_elev:.2f}m - ground: {ground_elev:.2f}m)")
            elif height_field in properties:
                height = float(properties[height_field])
                # If the value seems like an elevation (too high), use a reasonable default
                if height > 1000:  # Likely an elevation, not a height
                    height = 10.0  # Default building height
                    print(f"  - Using default height {height}m (original value {properties[height_field]} seems like elevation)")
            else:
                print(f"  - Warning: Height field '{height_field}' not found, using default 10m")
                height = 10.0
            
            # Handle MultiPolygon geometry
            if geometry.geom_type == 'MultiPolygon':
                print(f"  - MultiPolygon has {len(geometry.geoms)} individual polygons")
                valid_count = 0
                invalid_count = 0
                
                # Extract individual polygons from MultiPolygon
                for poly_idx, polygon in enumerate(geometry.geoms):
                    if polygon.is_valid and polygon.area > 0:
                        valid_count += 1
                        # Create new feature for each polygon
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
                    else:
                        invalid_count += 1
                        if invalid_count <= 5:  # Only show first few invalid polygons
                            print(f"    - Invalid polygon {poly_idx}: valid={polygon.is_valid}, area={polygon.area}")
                
                print(f"  - Valid polygons: {valid_count}, Invalid polygons: {invalid_count}")
            
            elif geometry.geom_type == 'Polygon':
                # Single polygon
                if geometry.is_valid and geometry.area > 0:
                    new_properties = properties.copy()
                    new_properties['height'] = height
                    new_properties['feature_id'] = idx
                    
                    feature_list.append({
                        'type': 'Feature',
                        'properties': new_properties,
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [list(geometry.exterior.coords)]
                        }
                    })
            
            else:
                print(f"  - Warning: Unsupported geometry type: {geometry.geom_type}")
        
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
    
    # Specify height field for your Calgary data
    height_field = "ROOFTOP__2"  # Use rooftop elevation as building height
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist!")
        print("Please create the directory and place your MultiPolygon .shp files there.")
        return
    
    # Find all shapefiles in input directory
    shapefiles = glob.glob(os.path.join(input_dir, "*.shp"))
    
    if not shapefiles:
        print(f"No .shp files found in '{input_dir}'")
        print("Please place your MultiPolygon shapefiles in the data/input/ directory.")
        return
    
    print(f"Found {len(shapefiles)} shapefile(s) to process:")
    for shp in shapefiles:
        print(f"  - {os.path.basename(shp)}")
    
    # Process all files
    all_features = []
    output_crs = None
    
    for shapefile in shapefiles:
        features, crs = process_multipolygon_file(shapefile, height_field)
        all_features.extend(features)
        
        # Use the CRS from the first file as output CRS
        if output_crs is None and crs is not None:
            output_crs = crs
    
    if not all_features:
        print("No valid building features found in any of the files!")
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
