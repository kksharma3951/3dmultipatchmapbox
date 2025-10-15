"""
Attribute-Based Height Converter
Uses building attributes (ROOFTOP - GROUND) instead of Z-coordinates.
This matches how the reference repo should work with proper height fields.
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon
import warnings
warnings.filterwarnings('ignore')


def process_multipolygon_file(filepath):
    """Process MultiPolygon using attribute-based height calculation."""
    print(f"Processing: {os.path.basename(filepath)}")
    
    try:
        # Read the shapefile
        gdf = gpd.read_file(filepath)
        print(f"  - Found {len(gdf)} features")
        
        # Convert timestamp columns to strings
        for col in gdf.columns:
            if gdf[col].dtype == 'datetime64[ns]' or 'datetime' in str(gdf[col].dtype):
                print(f"  - Converting timestamp column '{col}' to string")
                gdf[col] = gdf[col].astype(str)
        
        feature_list = []
        crs = gdf.crs
        
        # Process each feature
        for idx, row in gdf.iterrows():
            try:
                properties = row.drop('geometry').to_dict()
                geometry = row.geometry
                
                # Calculate building height from attributes (like reference repo)
                height = calculate_building_height(properties)
                
                if idx < 5:  # Print first 5 for debugging
                    print(f"  - Building {idx+1}: {height:.2f}m")
            except Exception as e:
                print(f"  - Error processing feature {idx}: {e}")
                continue
            
            # Handle MultiPolygon geometry
            if geometry.geom_type == 'MultiPolygon':
                # Iterate through each polygon in the MultiPolygon
                for poly_geom in geometry.geoms:
                    # Create new feature for each polygon
                    new_feature = properties.copy()
                    new_feature['height'] = height
                    
                    # Strip Z-coordinates if present and ensure valid geometry
                    if hasattr(poly_geom, 'exterior'):
                        # Convert to 2D coordinates (handle 3D coords)
                        coords_2d = [(x, y) for x, y, *z in poly_geom.exterior.coords]
                        try:
                            poly_2d = Polygon(coords_2d)
                            if poly_2d.is_valid and poly_2d.area > 0:
                                new_feature['geometry'] = poly_2d
                                feature_list.append(new_feature)
                        except Exception as e:
                            print(f"    - Warning: Invalid polygon: {e}")
                            continue
            else:
                # Single polygon
                new_feature = properties.copy()
                new_feature['height'] = height
                
                # Strip Z-coordinates if present
                if hasattr(geometry, 'exterior'):
                    coords_2d = [(x, y) for x, y, *z in geometry.exterior.coords]
                    try:
                        poly_2d = Polygon(coords_2d)
                        if poly_2d.is_valid and poly_2d.area > 0:
                            new_feature['geometry'] = poly_2d
                            feature_list.append(new_feature)
                    except Exception as e:
                        print(f"    - Warning: Invalid polygon: {e}")
                        continue
        
        print(f"  - Extracted {len(feature_list)} building polygons")
        return feature_list, crs
        
    except Exception as e:
        print(f"  - Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return [], None


def calculate_building_height(properties):
    """
    Calculate building height from attributes.
    This is how the reference repo should work with proper height fields.
    """
    
    # Method 1: Use ROOFTOP - GROUND elevation difference
    if 'ROOFTOP__2' in properties and 'GRD_ELEV_2' in properties:
        try:
            rooftop_elev = float(properties['ROOFTOP__2'])
            ground_elev = float(properties['GRD_ELEV_2'])
            height = max(0, rooftop_elev - ground_elev)
            
            # Sanity check: reasonable building height (0-300m)
            if 0 <= height <= 300:
                return height
            else:
                print(f"    - Unreasonable height {height:.2f}m, using default")
                return 10.0
                
        except (ValueError, TypeError):
            pass
    
    # Method 2: Use alternative elevation fields
    if 'ROOFTOP_EL' in properties and 'GRD_ELEV_M' in properties:
        try:
            rooftop_elev = float(properties['ROOFTOP_EL'])
            ground_elev = float(properties['GRD_ELEV_M'])
            height = max(0, rooftop_elev - ground_elev)
            
            # Sanity check: reasonable building height (0-300m)
            if 0 <= height <= 300:
                return height
            else:
                print(f"    - Unreasonable height {height:.2f}m, using default")
                return 10.0
                
        except (ValueError, TypeError):
            pass
    
    # Method 3: Use any available height-like field
    height_fields = ['HEIGHT', 'HEIGHT_M', 'BUILDING_H', 'ELEVATION']
    for field in height_fields:
        if field in properties:
            try:
                height = float(properties[field])
                if 0 <= height <= 300:
                    return height
            except (ValueError, TypeError):
                continue
    
    # Default height if no valid field found
    return 10.0


def main():
    """Main function to process all shapefiles and create GeoJSON output."""
    
    # Create output directory
    os.makedirs('data/output', exist_ok=True)
    
    # Find all shapefiles in input directory
    input_files = glob.glob('data/input/*.shp')
    
    if not input_files:
        print("No shapefiles found in data/input/")
        return
    
    print(f"Found {len(input_files)} shapefile(s) to process:")
    for file in input_files:
        print(f"  - {os.path.basename(file)}")
    
    all_features = []
    crs = None
    
    # Process each file
    for filepath in input_files:
        features, file_crs = process_multipolygon_file(filepath)
        all_features.extend(features)
        if crs is None:
            crs = file_crs
    
    if not all_features:
        print("No valid features found!")
        return
    
    print(f"\nTotal buildings extracted: {len(all_features)}")
    
    # Create GeoDataFrame and convert to WGS84
    gdf = gpd.GeoDataFrame(all_features, crs=crs)
    print("Converting to WGS84 (EPSG:4326) for web mapping...")
    gdf = gdf.to_crs('EPSG:4326')
    
    # Calculate height statistics
    heights = [f['height'] for f in all_features]
    print(f"\nBuilding Height Statistics:")
    print(f"  - Count: {len(heights)}")
    print(f"  - Min height: {min(heights):.2f} m")
    print(f"  - Max height: {max(heights):.2f} m")
    print(f"  - Average height: {sum(heights)/len(heights):.2f} m")
    
    # Save to GeoJSON
    output_file = 'data/output/buildings.geojson'
    gdf.to_file(output_file, driver='GeoJSON')
    
    print(f"\nConversion complete! GeoJSON saved to: {output_file}")
    print("You can now open index.html in your browser to visualize the 3D buildings.")


if __name__ == "__main__":
    main()
