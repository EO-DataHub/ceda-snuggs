from pystac import read_file, Item, Catalog, extensions, Asset, CatalogType
from urllib.parse import urlparse
from tqdm import tqdm
import shutil
from pathlib import Path
import click
import logging


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

        try:
            asset = item.assets[band_name]
            asset_href = fix_asset_href(asset.get_absolute_href())
        except KeyError:
            pass

    return (asset, asset_href)


def fix_asset_href(uri):

    parsed = urlparse(uri)

    if parsed.scheme.startswith("http"):

        return "/vsicurl/{}".format(uri)

    elif parsed.scheme.startswith("file"):

        return uri.replace("file://", "")

    else:

        return uri

def write_local_stac(stac: Catalog, output_stac_path: Path, title: str, description: str) -> None:
    stac.set_self_href(output_stac_path.as_posix())
    stac.title = title
    stac.description = description
    stac.make_all_asset_hrefs_relative()
    stac.normalize_and_save(output_stac_path.as_posix(), catalog_type=CatalogType.SELF_CONTAINED)

def merge_stac_catalogs(stac_catalog_dirs: list[Path], output_dir: Path) -> None:
    # Create an empty root catalog for the merged output
    merged_catalog = Catalog(id="", description="Merged STAC Catalog")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_data_dir = output_dir / "source_data"
    source_data_dir.mkdir(parents=True, exist_ok=True)

    # Create list to track copied items
    copied_items = set()

    for dir_path in tqdm(stac_catalog_dirs, desc="Joining STAC Catalogs"):
        catalog_path = dir_path / "catalog.json"

        if not catalog_path.exists():
            click.echo(f"Skipping {dir_path} (catalog.json not found)")
            continue

        # Load the catalog
        input_catalog = Catalog.from_file(str(catalog_path))
        input_catalog.make_all_asset_hrefs_absolute()

        # Traverse and process each item
        for item in input_catalog.get_items(recursive=True):
            # Create a folder for the item's assets in the source_data directory
            item_assets_dir = source_data_dir / item.id
            item_assets_dir.mkdir(parents=True, exist_ok=True)

            logging.info(f"Processing item {item.id} from catalog {dir_path.name}")
            logging.info(item.assets.values())

            # Copy each asset to the new folder
            for asset in item.assets.values():
                asset_path = Path(asset.href)
                if asset_path.exists():
                    new_asset_path = item_assets_dir / asset_path.name
                    shutil.copy2(asset_path, new_asset_path)
                    asset.href = new_asset_path.absolute().as_posix()

            if item.id in copied_items:
                logging.info(f"Item {item.id} already processed, just adding assets.")
                copied_item = merged_catalog.get_item(item.id)
                copied_item.assets.update(item.assets)
                item = copied_item
            else:
                copied_items.add(item.id)

            # Add the item to the merged catalog
            merged_catalog.add_item(item)

    # Save the merged catalog to the output directory
    merged_catalog.make_all_asset_hrefs_relative()
    merged_catalog.normalize_and_save(output_dir.as_posix(), catalog_type=CatalogType.SELF_CONTAINED)

