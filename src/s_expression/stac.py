from pystac import read_file, Item, Catalog, extensions
from urllib.parse import urlparse
import gdal


def get_item(reference):

    stac_thing = read_file(reference)

    if isinstance(stac_thing, Item):
        return stac_thing

    else:

        try:

            collection = next(stac_thing.get_children())
            item = next(collection.get_items())

        except StopIteration:

            item = next(stac_thing.get_items())

        return item


def get_asset(item, band_name):

    asset = None
    asset_href = None

    eo_item = extensions.eo.EOExtension.ext(item)

    # Get bands
    if (eo_item.bands) is not None:

        for index, band in enumerate(eo_item.bands):

            if band.common_name in [band_name]:

                asset = item.assets[band.name]
                asset_href = fix_asset_href(asset.get_absolute_href())
                break

    # read the asset key (no success with common band name)
    if asset is None:

        asset = item.assets[band_name]
        asset_href = fix_asset_href(asset.get_absolute_href())

    return (asset, asset_href)


def fix_asset_href(uri):

    parsed = urlparse(uri)

    if parsed.scheme.startswith("http"):

        return "/vsicurl/{}".format(uri)

    elif parsed.scheme.startswith("file"):

        return uri.replace("file://", "")

    else:

        return uri
