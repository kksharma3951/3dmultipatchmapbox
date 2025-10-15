"""
ESRI Multipatch to GeoJSON Converter for Mapbox 3D Visualization

Adapted from bbonczak/multipatch_convertor
Converts multiple multipatch shapefiles to a single GeoJSON file for 3D building visualization.

Usage:
    python converter.py

Requirements:
    - Place your multipatch .shp files in data/input/
    - Output will be saved to data/output/buildings.geojson
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon
import warnings
warnings.filterwarnings('ignore')


def process_multipatch_file(filepath, z_unit_in='m', z_unit_out='m', relative_h=False):
    """
    Process a single multipatch shapefile and return features list.
    
    Args:
        filepath: Path to the shapefile
        z_unit_in: Input height units ('m' or 'ft')
        z_unit_out: Output height units ('m' or 'ft') 
        relative_h: Whether to calculate relative height (subtract minimum)
    
    Returns:
        List of GeoJSON features with height attributes
    """
    print(f"Processing: {os.path.basename(filepath)}")
    
    try:
        # Read the shapefile
        gdf = gpd.read_file(filepath)
        print(f"  - Found {len(gdf)} features")
        
        # Get CRS
        crs = gdf.crs
        print(f"  - CRS: {crs}")
        
        # Convert timestamp columns to strings to avoid JSON serialization errors
        for col in gdf.columns:
            if gdf[col].dtype == 'datetime64[ns]' or 'datetime' in str(gdf[col].dtype):
                print(f"  - Converting timestamp column '{col}' to string")
                gdf[col] = gdf[col].astype(str)
        
        # Convert to JSON structure for processing
        gdf_json = json.loads(gdf.to_json())
        
        feature_list = []
        
        # Process each feature
        for feature in gdf_json['features']:
            properties = feature['properties'].copy()
            
            # Extract coordinates from multipatch geometry
            coords = feature['geometry']['coordinates']
            
            # Define minimum height threshold
            if z_unit_in == 'm':
                min_h = 9000  # 9km in meters
            else:
                min_h = 30000  # 30k feet
            
            # Process multipatch coordinates (list of polygons)
            for mp in coords:  # Each multipatch
                for polygon in mp:  # Each polygon in multipatch
                    # Extract vertices and flatten to 2D
                    vertices_2d = []
                    min_z = float('inf')
                    max_z = float('-inf')
                    
                    for vertex in polygon:
                        if len(vertex) >= 3:  # Has Z coordinate
                            x, y, z = vertex[0], vertex[1], vertex[2]
                            vertices_2d.append([x, y])  # 2D coordinates
                            
                            # Track height range
                            if z < min_z:
                                min_z = z
                            if z > max_z:
                                max_z = z
                    
                    # Skip if not enough vertices or invalid height
                    if len(vertices_2d) < 3 or max_z <= min_z:
                        continue
                    
                    # Calculate building height
                    height = max_z - min_z
                    
                    # Skip buildings that are too small
                    if height < 0.1:  # Less than 10cm
                        continue
                    
                    # Update minimum height tracking
                    if height < min_h:
                        min_h = height
                    
                    # Create new feature
                    new_feature = properties.copy()
                    new_feature['height'] = height
                    new_feature['min_z'] = min_z
                    new_feature['max_z'] = max_z
                    
                    # Create 2D polygon geometry
                    try:
                        polygon_geom = Polygon(vertices_2d)
                        if polygon_geom.is_valid:
                            new_feature['geometry'] = polygon_geom
                            feature_list.append(new_feature)
                    except Exception as e:
                        print(f"  - Warning: Invalid polygon geometry: {e}")
                        continue
        
        # Adjust heights if relative_h is True
        if relative_h and feature_list:
            for feature in feature_list:
                feature['height'] = feature['height'] - min_h
        
        # Convert height units if needed
        if z_unit_in != z_unit_out:
            if z_unit_in == 'm' and z_unit_out == 'ft':
                for feature in feature_list:
                    feature['height'] *= 3.28084
            elif z_unit_in == 'ft' and z_unit_out == 'm':
                for feature in feature_list:
                    feature['height'] *= 0.3048
        
        print(f"  - Extracted {len(feature_list)} valid building footprints")
        return feature_list, crs
        
    except Exception as e:
        print(f"  - Error processing file: {e}")
        return [], None


def main():
    """Main function to process all multipatch files and create GeoJSON output."""
    
    # Input and output directories
    input_dir = "data/input"
    output_dir = "data/output"
    output_file = os.path.join(output_dir, "buildings.geojson")
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist!")
        print("Please create the directory and place your multipatch .shp files there.")
        return
    
    # Find all shapefiles in input directory
    shapefiles = glob.glob(os.path.join(input_dir, "*.shp"))
    
    if not shapefiles:
        print(f"No .shp files found in '{input_dir}'")
        print("Please place your multipatch shapefiles in the data/input/ directory.")
        return
    
    print(f"Found {len(shapefiles)} shapefile(s) to process:")
    for shp in shapefiles:
        print(f"  - {os.path.basename(shp)}")
    
    # Process all files
    all_features = []
    output_crs = None
    
    for shapefile in shapefiles:
        features, crs = process_multipatch_file(shapefile)
        all_features.extend(features)
        
        # Use the CRS from the first file as output CRS
        if output_crs is None and crs is not None:
            output_crs = crs
    
    if not all_features:
        print("No valid building features found in any of the files!")
        return
    
    print(f"\nTotal buildings extracted: {len(all_features)}")
    
    # Create GeoDataFrame from all features
    gdf = gpd.GeoDataFrame(all_features, crs=output_crs)
    
    # Convert to WGS84 (EPSG:4326) for Mapbox compatibility
    print("Converting to WGS84 (EPSG:4326) for web mapping...")
    gdf = gdf.to_crs('EPSG:4326')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as GeoJSON
    print(f"Saving to: {output_file}")
    gdf.to_file(output_file, driver='GeoJSON')
    
    # Print summary statistics
    heights = [f['height'] for f in all_features]
    print(f"\nBuilding Height Statistics:")
    print(f"  - Count: {len(heights)}")
    print(f"  - Min height: {min(heights):.2f} m")
    print(f"  - Max height: {max(heights):.2f} m")
    print(f"  - Average height: {sum(heights)/len(heights):.2f} m")
    
    print(f"\nConversion complete! GeoJSON saved to: {output_file}")
    print("You can now open index.html in your browser to visualize the 3D buildings.")


if __name__ == "__main__":
    main()
