"""
Correct ESRI Multipatch to GeoJSON Converter

Based on the original bbonczak approach:
- Extract Z-coordinates directly from 3D polygon vertices as height
- Strip Z-coordinates to get 2D polygons for Mapbox
- Each polygon gets its own height from its Z-coordinates

This is the CORRECT way to handle multipatch data for Mapbox.
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon
import warnings
warnings.filterwarnings('ignore')


def multipatch_converter(geodataframe, z_unit_in='m', z_unit_out='m', relative_h=False, save=False, path='./', filename='output', out_format='geojson'):
    """
    Convert ESRI Multipatch to 2D polygons with height attributes.
    
    Based on the original bbonczak implementation.
    """
    print(f"Processing {len(geodataframe)} features...")
    
    # Extract CRS
    crs = geodataframe.crs
    print(f"CRS: {crs}")
    
    # Convert to JSON structure
    gdf_json = json.loads(geodataframe.to_json())
    
    # Initiate list of features
    feature_list = []
    
    # Iterate through features of GeoDataFrame
    for feature in gdf_json['features']:
        # Extract properties of each feature
        properties = feature['properties']
        
        # Flatten MultiPolygons into list of Polygons
        polygon_list = [p for mp in feature['geometry']['coordinates'] for p in mp]
        
        # Iterate through Polygon list
        for polygon in polygon_list:
            # Create new feature and assign properties to each Polygon
            new_feature = properties.copy()
            
            # Extract height from Z-coordinates (calculate building height)
            z_values = [vertex[2] for vertex in polygon if len(vertex) >= 3]
            if z_values:
                height = max(z_values) - min(z_values)  # Building height = max - min Z
                height = max(0, height)  # Ensure positive height
            else:
                height = 10.0  # Default height if no Z values
            
            # Convert height units if needed
            if z_unit_in == 'm' and z_unit_out == 'ft':
                height = height * 3.28084
            elif z_unit_in == 'ft' and z_unit_out == 'm':
                height = height * 0.3048
            
            # Assign new feature's height and vertices (strip Z-coordinates)
            new_feature['height'] = height
            new_feature['geometry'] = Polygon([vertex[:2] for vertex in polygon])
            
            # Populate polygon list
            feature_list.append(new_feature)
    
    # Create a GeoDataFrame from new features
    new_gdf = gpd.GeoDataFrame(feature_list, index=range(len(feature_list)), crs=crs)
    
    # Convert CRS to WGS 84 (lat and long in degrees)
    print("Converting to WGS84 (EPSG:4326)...")
    new_gdf.to_crs({'init': 'epsg:4326'}, inplace=True)
    
    if save:
        if out_format == 'geojson':
            new_gdf.to_file(f'{path}/{filename}.geojson', driver='GeoJSON')
        elif out_format == 'shp':
            new_gdf.to_file(f'{path}/{filename}.shp')
        print(f"Saved to: {path}/{filename}.{out_format}")
    
    return new_gdf


def main():
    """Main function to process all multipatch files."""
    
    # Input and output directories
    input_dir = "data/input"
    output_dir = "data/output"
    
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
    
    for shapefile in shapefiles:
        print(f"\nProcessing: {os.path.basename(shapefile)}")
        
        try:
            # Read the shapefile
            gdf = gpd.read_file(shapefile)
            print(f"  - Found {len(gdf)} features")
            print(f"  - Geometry types: {gdf.geometry.geom_type.unique()}")
            
            # Convert timestamp columns to strings to avoid JSON serialization errors
            for col in gdf.columns:
                if gdf[col].dtype == 'datetime64[ns]' or 'datetime' in str(gdf[col].dtype):
                    print(f"  - Converting timestamp column '{col}' to string")
                    gdf[col] = gdf[col].astype(str)
            
            # Use the correct converter
            converted_gdf = multipatch_converter(
                gdf, 
                z_unit_in='m', 
                z_unit_out='m', 
                relative_h=False, 
                save=False
            )
            
            # Add to all features
            for _, row in converted_gdf.iterrows():
                feature = {
                    'type': 'Feature',
                    'properties': row.drop('geometry').to_dict(),
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [list(row.geometry.exterior.coords)]
                    }
                }
                all_features.append(feature)
            
            print(f"  - Extracted {len(converted_gdf)} building polygons")
            
        except Exception as e:
            print(f"  - Error processing file: {e}")
            continue
    
    if not all_features:
        print("No valid building features found!")
        return
    
    print(f"\nTotal buildings extracted: {len(all_features)}")
    
    # Create final GeoDataFrame
    final_gdf = gpd.GeoDataFrame.from_features(all_features, crs='EPSG:4326')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as GeoJSON
    output_file = os.path.join(output_dir, "buildings.geojson")
    final_gdf.to_file(output_file, driver='GeoJSON')
    
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
