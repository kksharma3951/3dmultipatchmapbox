"""
Original bbonczak converter variant:
- Keeps original logic/structure
- Per sub-polygon height = max(Z) - min(Z)
- Also stores min_z and max_z in properties
"""

import json
import os
import glob
import geopandas as gpd
from shapely.geometry import Polygon
import warnings
warnings.filterwarnings('ignore')


def multipatch_convertor_relative(geodataframe, z_unit_in='m', z_unit_out='m', relative_h=False, save=False, path='./', filename='output', out_format='geojson'):
    """Same interface as original, but height per sub-polygon is max(Z)-min(Z)."""

    crs = geodataframe.crs
    gdf_gj = json.loads(geodataframe.to_json())

    feature_list = []

    for feature in gdf_gj['features']:
        properties = feature['properties']
        polygon_list = [p for mp in feature['geometry']['coordinates'] for p in mp]

        # Set a very large minimum reference for relative adjustment
        min_h = 9000 if z_unit_in == 'm' else 30000

        splitted_feature_list = []

        for polygon in polygon_list:
            new_feature = properties.copy()

            # Compute per-subpolygon min/max Z
            z_vals = [v[2] for v in polygon if len(v) >= 3]
            if not z_vals:
                # Fallback: keep original behavior if no Z found
                height = 0.0
                min_z = 0.0
                max_z = 0.0
            else:
                min_z = min(z_vals)
                max_z = max(z_vals)
                height = max(0.0, max_z - min_z)

            if height < min_h:
                min_h = height

            new_feature['height'] = height
            new_feature['min_z'] = float(min_z)
            new_feature['max_z'] = float(max_z)
            new_feature['geometry'] = Polygon([vertex[:2] for vertex in polygon])

            splitted_feature_list.append(new_feature)

        if relative_h:
            for f in splitted_feature_list:
                f['height'] = f['height'] - min_h

        if (z_unit_in == 'm') & (z_unit_out == 'ft'):
            for f in splitted_feature_list:
                f['height'] = f['height'] * 3.28084
        elif (z_unit_in == 'ft') & (z_unit_out == 'm'):
            for f in splitted_feature_list:
                f['height'] = f['height'] * 0.3048
        elif z_unit_in == z_unit_out:
            pass
        else:
            raise NameError('wrongUnits')

        feature_list = feature_list + splitted_feature_list

    new_gdf_gj = gpd.GeoDataFrame(feature_list, index=range(len(feature_list)), crs=crs)
    new_gdf_gj.to_crs({'init': 'epsg:4326'}, inplace=True)

    if save:
        if out_format == 'geojson':
            new_gdf_gj.to_file(f"{path}{filename}.geojson", driver='GeoJSON')
        elif out_format == 'shp':
            new_gdf_gj.to_file(f"{path}{filename}.shp")
        else:
            raise NameError('wrongFormat')
    else:
        return new_gdf_gj


def main():
    os.makedirs('data/output', exist_ok=True)
    input_files = glob.glob('data/input/*.shp')
    if not input_files:
        print('No shapefiles found in data/input/')
        return

    print(f"Found {len(input_files)} shapefile(s) to process:")
    for f in input_files:
        print(f"  - {os.path.basename(f)}")

    for filepath in input_files:
        print(f"\nProcessing: {os.path.basename(filepath)}")
        gdf = gpd.read_file(filepath)
        print(f"  - Found {len(gdf)} features")

        for col in gdf.columns:
            if gdf[col].dtype == 'datetime64[ns]' or 'datetime' in str(gdf[col].dtype):
                print(f"  - Converting timestamp column '{col}' to string")
                gdf[col] = gdf[col].astype(str)

        print("  - Using relative per-subpolygon height (maxZ - minZ)...")
        result_gdf = multipatch_convertor_relative(gdf, z_unit_in='m', z_unit_out='m', relative_h=False, save=False)
        print(f"  - Extracted {len(result_gdf)} building polygons")

        heights = result_gdf['height'].tolist()
        if heights:
            print("\nPer-subpolygon Height Statistics:")
            print(f"  - Count: {len(heights)}")
            print(f"  - Min: {min(heights):.2f} m | Max: {max(heights):.2f} m | Avg: {sum(heights)/len(heights):.2f} m")

        output_file = 'data/output/buildings.geojson'
        result_gdf.to_file(output_file, driver='GeoJSON')
        print(f"\nSaved GeoJSON to: {output_file}")
        break


if __name__ == '__main__':
    main()


