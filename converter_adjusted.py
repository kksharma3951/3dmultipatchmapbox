"""
Original bbonczak multipatch_convertor.py with height adjustment
Uses the original function but adjusts absolute elevations to relative building heights
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon 
import warnings
warnings.filterwarnings('ignore')


def multipatch_convertor(geodataframe, z_unit_in='m', z_unit_out='m', relative_h=False, save=False, path='./', filename='output', out_format='geojson'):
    
    """Function converting ESRI Multipatch file into single polygons with 
    assignned height attribute using GeoPandas. It allows conversion between 
    meters ('m') and feets ('ft'), as well as assigning relative height.
    
    Dependencies:
        geopandas==0.3.0
        json==2.0.9
        shapely==1.5.16

    Keyword arguments:
    geodataframe: geopandas.GeoDataFrame() object
            GeoDataFrame to be converted;
    z_unit_in: str, {'m', 'ft'}, default 'm'
            height units of the input GeoDataFrame;
    z_unit_out: str, {'m', 'ft'}, default 'm'
            height units of the output GeoDataFrame;
    relative_h: bool, default False
            If the output GeoDataFrame should present relative height (Applies 
            when minimum height value is not equal to 0). All height values will 
            be subtructed minimum height of the feature.
    save: bool, default False
            whether the function should create an object in memory or save it 
            to file.
    path: str, default './'
            if 'save' is set to True, defines directory where to save the output
    filename: str, default 'output'
            if 'save' is set to True, defines the output name of the file
    out_format: str, {'geojson', 'shp'}, default 'geojson'
            if 'save' is set to True, defines the output file format between
            GeoJSON and ESRI Shapefile
    """   
    
    # Extract Coordinate Reference System (CRS) of the GeoDataFrame
    crs = geodataframe.crs
    
    # Convert GeoDataFrame inot JSON structure
    gdf_gj = json.loads(geodataframe.to_json())
    
    # Initiate list of features
    feature_list = []

    # Iterate through features of GeoDataFrame
    for feature in gdf_gj['features']:
        # Extract properties of each feature
        properties = feature['properties']
        # Flatten MultiPolygons into list of Polygons
        polygon_list = [p for mp in feature['geometry']['coordinates'] for p in mp]
        
        # Define minimum height
        if z_unit_in == 'm':
            min_h = 9000
        else:
            min_h = 30000
        
        # Initiate Polygon list for the feature
        splitted_feature_list = []
        
        # Iterate through Polygon list
        for polygon in polygon_list:
            # Create new feature and assign properties to each Polygon
            new_feature = properties.copy()
            
            # Extract new_feature height
            height = polygon[0][2]
            
            # Compare height to minimum height and save if smaller
            if height < min_h:
                min_h = height
            
            # Assign new feature's height and vertices
            new_feature['height'] = height
            new_feature['geometry'] = Polygon([vertex[:2] for vertex in polygon])

            # Populate polygon list
            splitted_feature_list.append(new_feature)
            
        # Adjust height if relative
        if relative_h:
            for f in splitted_feature_list:
                f['height']=f['height'] - min_h
             
        # Convert height units
        if (z_unit_in == 'm') & (z_unit_out == 'ft'):
            for f in splitted_feature_list:
                f['height']=f['height'] * 3.28084
        elif (z_unit_in == 'ft') & (z_unit_out == 'm'):
            for f in splitted_feature_list:
                f['height']=f['height'] * 0.3048
        elif z_unit_in == z_unit_out:
            pass
        else:
            raise NameError('wrongUnits')
            print('Wrong height units given! Please, choose either \'m\' for meters or \'ft\' for feets')            
                
        # Add extracted new_features to global feature list
        feature_list = feature_list + splitted_feature_list

    # Create a GeoDataFrame from new features
    new_gdf_gj = gpd.GeoDataFrame(
        feature_list, 
        index=range(len(feature_list)), 
        crs=crs)
    
    # Convert CRS to WGS 84 (lat and long in degrees)
    new_gdf_gj.to_crs({'init':'epsg:4326'}, inplace=True)
    
    # save file in desired location and format or return a GeoDataFrame
    if save:
        if out_format == 'geojson':
            new_gdf_gj.to_file(
                '{}{}.geojson'.format(path, filename), 
                driver='GeoJSON')
        elif out_format == 'shp':
            new_gdf_gj.to_file('{}{}.shp'.format(path, filename))
        else:
            raise NameError('wrongFormat')
            print('Wrong output file format given! Please, choose either \'geojson\' or \'shp\'')
    else:
        return new_gdf_gj


def adjust_heights_to_building_heights(gdf):
    """
    Convert absolute elevations to relative building heights.
    This makes buildings appear at ground level with proper building heights.
    """
    print("Adjusting heights from absolute elevations to relative building heights...")
    
    # Get all height values
    heights = gdf['height'].tolist()
    min_elevation = min(heights)
    max_elevation = max(heights)
    
    print(f"  - Original elevation range: {min_elevation:.2f}m to {max_elevation:.2f}m")
    
    # For each building, calculate relative height
    adjusted_features = []
    
    for idx, row in gdf.iterrows():
        # Get all polygons that belong to the same building (same STRUCT_ID if available)
        if 'STRUCT_ID' in row:
            struct_id = row['STRUCT_ID']
            # Find all polygons with same STRUCT_ID
            same_building = gdf[gdf['STRUCT_ID'] == struct_id]
            building_heights = same_building['height'].tolist()
            building_min = min(building_heights)
            building_max = max(building_heights)
            building_height = building_max - building_min
        else:
            # If no STRUCT_ID, use individual polygon height
            building_height = max(10.0, row['height'] - min_elevation)
        
        # Create new feature with adjusted height
        new_feature = row.copy()
        new_feature['height'] = max(5.0, building_height)  # Minimum 5m height
        new_feature['original_elevation'] = row['height']  # Keep original for reference
        adjusted_features.append(new_feature)
    
    # Create new GeoDataFrame
    adjusted_gdf = gpd.GeoDataFrame(adjusted_features, crs=gdf.crs)
    
    # Calculate new height statistics
    new_heights = adjusted_gdf['height'].tolist()
    print(f"  - Adjusted height range: {min(new_heights):.2f}m to {max(new_heights):.2f}m")
    print(f"  - Average building height: {sum(new_heights)/len(new_heights):.2f}m")
    
    return adjusted_gdf


def main():
    """Main function to process all shapefiles using the original bbonczak function with height adjustment."""
    
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
    
    # Process each file using the original function
    for filepath in input_files:
        print(f"\nProcessing: {os.path.basename(filepath)}")
        
        try:
            # Read the shapefile
            gdf = gpd.read_file(filepath)
            print(f"  - Found {len(gdf)} features")
            
            # Convert timestamp columns to strings (to avoid JSON serialization issues)
            for col in gdf.columns:
                if gdf[col].dtype == 'datetime64[ns]' or 'datetime' in str(gdf[col].dtype):
                    print(f"  - Converting timestamp column '{col}' to string")
                    gdf[col] = gdf[col].astype(str)
            
            # Use the original bbonczak function exactly as-is
            print("  - Using original bbonczak multipatch_convertor function...")
            result_gdf = multipatch_convertor(
                geodataframe=gdf,
                z_unit_in='m',
                z_unit_out='m', 
                relative_h=False,
                save=False
            )
            
            print(f"  - Extracted {len(result_gdf)} building polygons")
            
            # Calculate original height statistics
            original_heights = result_gdf['height'].tolist()
            print(f"\nOriginal Height Statistics (Absolute Elevations):")
            print(f"  - Count: {len(original_heights)}")
            print(f"  - Min elevation: {min(original_heights):.2f} m")
            print(f"  - Max elevation: {max(original_heights):.2f} m")
            print(f"  - Average elevation: {sum(original_heights)/len(original_heights):.2f} m")
            
            # Adjust heights to building heights
            adjusted_gdf = adjust_heights_to_building_heights(result_gdf)
            
            # Save to GeoJSON
            output_file = 'data/output/buildings.geojson'
            adjusted_gdf.to_file(output_file, driver='GeoJSON')
            
            print(f"\nConversion complete! GeoJSON saved to: {output_file}")
            print("You can now open index.html in your browser to visualize the 3D buildings.")
            
            break  # Process only the first file for now
            
        except Exception as e:
            print(f"  - Error processing file: {e}")
            import traceback
            traceback.print_exc()
            continue


if __name__ == "__main__":
    main()
