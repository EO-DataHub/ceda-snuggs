import os
import snuggs
import re
import gdal
import numpy as np
from collections import OrderedDict
from .stac import get_asset
import logging


def get_resolution(item, s_expression, assets):

    resolution = 10000
    if assets:
        asset_names = assets
    else:
        asset_names = parse_expression(s_expression)

    for index, asset_name in enumerate(asset_names):

        _, asset_href = get_asset(item, asset_name)

        if not asset_href:

            continue

        _ds = gdal.Open(asset_href)

        if resolution >= _ds.GetGeoTransform()[1]:

            resolution = _ds.GetGeoTransform()[1]

    return resolution


def pre_process(item, s_expression, assets):

    assets_dict = OrderedDict()

    resolution = get_resolution(item, s_expression, assets)

    # Will extract assets based on required bands
    if assets:
        asset_names = assets
    else:
        asset_names = parse_expression(s_expression)

    for index, asset_name in enumerate(asset_names):

        _, asset_href = get_asset(item, asset_name)

        if not asset_href:

            continue

        _ds = gdal.Open(asset_href)

        if _ds.GetGeoTransform()[1] == resolution:

            assets_dict[asset_name] = asset_href

        else:

            gdal.Translate(
                "{}_{}.tif".format(asset_name, resolution),
                _ds,
                xRes=resolution,
                yRes=resolution,
            )

            assets_dict[asset_name] = "{}_{}.tif".format(asset_name, resolution)

    return assets_dict


def get_empty_ds(ds, out_tif, band_count):

    driver = gdal.GetDriverByName("GTiff")

    data_type = gdal.GDT_Float32 if band_count == 1 else gdal.GDT_Byte
    dst_ds = driver.Create(
        out_tif, ds.RasterXSize, ds.RasterYSize, band_count, data_type
    )

    dst_ds.SetGeoTransform(ds.GetGeoTransform())
    dst_ds.SetProjection(ds.GetProjectionRef())

    return dst_ds


def get_size(offset, block_size, size):

    if offset + block_size > size:

        return size - offset

    else:

        return block_size


def get_block_size(band):

    return band.GetBlockSize()[0], band.GetBlockSize()[1]


def parse_expression(s_expression):

    bands = s_expression

    snuggs_keywords = ["interp", "where", "(", ")", "="]

    for k in (
        snuggs_keywords
        + list(snuggs.op_map.keys())
        + list(snuggs.func_map.keys())
        + list(snuggs.higher_func_map.keys())
    ):

        bands = bands.replace(k, " ")

    bands = re.sub(" +", " ", bands).strip().split(" ")

    bands = list(dict.fromkeys(bands))

    return bands


def apply_s_expression(item, out_tif, s_expression, assets):
    # reads an input tif, applies the expression and writes the output tif
    # uses blocks to reduce the memory footprint
    asset_hrefs = pre_process(item, s_expression, assets)

    if not asset_hrefs:
        logging.error("No assets found")
        if not assets:
            logging.error("Consider specifying assets in inputs")
        else:
            logging.error("Provided assets not found in item, check spelling")
        return

    common_band_names = parse_expression(s_expression)

    logging.info(f"Processing {len(asset_hrefs)} assets")
    logging.info(f"Assets: {asset_hrefs.keys()}")

    ds = gdal.Open(list(asset_hrefs.values())[0])

    dst_ds = get_empty_ds(ds, "temp.tif", 1)

    # read the block size, we assume it's the same for all bands
    band = ds.GetRasterBand(1)

    x_block_size, y_block_size = get_block_size(band)

    blocks = 0

    for offset_y in range(0, ds.RasterYSize, y_block_size):

        rows = get_size(offset_y, y_block_size, ds.RasterYSize)

        for offset_x in range(0, ds.RasterXSize, x_block_size):

            cols = get_size(offset_x, x_block_size, ds.RasterXSize)

            ctx = dict()

            for asset_name, asset_href in asset_hrefs.items():

                _ds = gdal.Open(asset_href)

                if assets:
                    for i in range(1, _ds.RasterCount + 1):
                        _band = _ds.GetRasterBand(i)

                        if _band.GetDescription() in common_band_names:

                            ctx[_band.GetDescription()] = _band.ReadAsArray(
                                offset_x, offset_y, cols, rows
                            ).astype(float)

                else:
                    _band = _ds.GetRasterBand(1)

                    ctx[asset_name] = _band.ReadAsArray(
                        offset_x, offset_y, cols, rows
                    ).astype(float)

                _band = None

                _ds = None

            arr = snuggs.eval(s_expression, **ctx)

            del ctx

            dst_ds.GetRasterBand(1).WriteArray(arr, offset_x, offset_y)

            del arr

            blocks += 1

    driver = gdal.GetDriverByName("GTiff")

    dst_ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64])

    output = driver.CreateCopy(
        os.path.join(out_tif),
        dst_ds,
        options=["COPY_SRC_OVERVIEWS=YES", "TILED=YES", "COMPRESS=DEFLATE"],
    )

    logging.info(f"Data saved to {os.path.join(out_tif)}")

    os.remove("temp.tif")
