"""
Simple MultiPolygon to GeoJSON Converter

A more robust version that handles geometry issues better.
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon
import warnings
warnings.filterwarnings('ignore')


def process_multipolygon_file(filepath):
    """Process a MultiPolygon shapefile with robust geometry handling."""
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
            if idx >= 10:  # Process only first 10 buildings for testing
                break
                
            properties = row.drop('geometry').to_dict()
            geometry = row.geometry
            
            # Calculate building height
            if 'ROOFTOP__2' in properties and 'GRD_ELEV_2' in properties:
                rooftop_elev = float(properties['ROOFTOP__2'])
                ground_elev = float(properties['GRD_ELEV_2'])
                height = max(0, rooftop_elev - ground_elev)
                print(f"  - Building {idx+1}: {height:.2f}m")
            else:
                height = 10.0
                print(f"  - Building {idx+1}: Using default height {height}m")
            
            # Handle geometry - try different approaches
            polygons_processed = 0
            
            try:
                # Method 1: Try to explode MultiPolygon
                if geometry.geom_type == 'MultiPolygon':
                    exploded = gdf.iloc[[idx]].explode(index_parts=True)
                    for poly_idx, (_, poly_row) in enumerate(exploded.iterrows()):
                        poly_geom = poly_row.geometry
                        if poly_geom.geom_type == 'Polygon' and poly_geom.is_valid and poly_geom.area > 0:
                            # Create feature
                            new_properties = properties.copy()
                            new_properties['height'] = height
                            new_properties['polygon_id'] = poly_idx
                            new_properties['feature_id'] = idx
                            
                            feature_list.append({
                                'type': 'Feature',
                                'properties': new_properties,
                                'geometry': {
                                    'type': 'Polygon',
                                    'coordinates': [list(poly_geom.exterior.coords)]
                                }
                            })
                            polygons_processed += 1
                
                # Method 2: If explode didn't work, try direct iteration
                elif geometry.geom_type == 'MultiPolygon' and hasattr(geometry, 'geoms'):
                    for poly_idx, polygon in enumerate(geometry.geoms):
                        if hasattr(polygon, 'exterior') and polygon.is_valid and polygon.area > 0:
                            # Clean coordinates (remove Z values)
                            coords = [(coord[0], coord[1]) for coord in polygon.exterior.coords]
                            
                            new_properties = properties.copy()
                            new_properties['height'] = height
                            new_properties['polygon_id'] = poly_idx
                            new_properties['feature_id'] = idx
                            
                            feature_list.append({
                                'type': 'Feature',
                                'properties': new_properties,
                                'geometry': {
                                    'type': 'Polygon',
                                    'coordinates': [coords]
                                }
                            })
                            polygons_processed += 1
                
                # Method 3: Single Polygon
                elif geometry.geom_type == 'Polygon' and geometry.is_valid and geometry.area > 0:
                    coords = [(coord[0], coord[1]) for coord in geometry.exterior.coords]
                    
                    new_properties = properties.copy()
                    new_properties['height'] = height
                    new_properties['feature_id'] = idx
                    
                    feature_list.append({
                        'type': 'Feature',
                        'properties': new_properties,
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [coords]
                        }
                    })
                    polygons_processed += 1
                
                print(f"  - Building {idx+1}: Processed {polygons_processed} polygons")
                
            except Exception as e:
                print(f"  - Building {idx+1}: Error processing geometry: {e}")
                continue
        
        print(f"  - Extracted {len(feature_list)} building polygons")
        return feature_list, crs
        
    except Exception as e:
        print(f"  - Error processing file: {e}")
        return [], None


def main():
    """Main function."""
    input_dir = "data/input"
    output_dir = "data/output"
    output_file = os.path.join(output_dir, "buildings.geojson")
    
    # Find shapefiles
    shapefiles = glob.glob(os.path.join(input_dir, "*.shp"))
    
    if not shapefiles:
        print(f"No .shp files found in '{input_dir}'")
        return
    
    print(f"Found {len(shapefiles)} shapefile(s) to process")
    
    # Process files
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
    
    # Create GeoDataFrame and save
    gdf = gpd.GeoDataFrame.from_features(all_features, crs=output_crs)
    
    print("Converting to WGS84 (EPSG:4326)...")
    gdf = gdf.to_crs('EPSG:4326')
    
    os.makedirs(output_dir, exist_ok=True)
    gdf.to_file(output_file, driver='GeoJSON')
    
    # Statistics
    heights = [f['properties']['height'] for f in all_features]
    print(f"\nBuilding Height Statistics:")
    print(f"  - Count: {len(heights)}")
    print(f"  - Min height: {min(heights):.2f} m")
    print(f"  - Max height: {max(heights):.2f} m")
    print(f"  - Average height: {sum(heights)/len(heights):.2f} m")
    
    print(f"\nConversion complete! GeoJSON saved to: {output_file}")


if __name__ == "__main__":
    main()


