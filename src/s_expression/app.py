import os
import sys
import logging
import click
from click2cwl import dump
import logging
from .s_expression import apply_s_expression
from typing import Optional
from .stac import get_item, merge_stac_catalogs
from pystac import Item, Asset, MediaType, extensions, Catalog, CatalogType

import shutil
from pathlib import Path
import json


logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

@click.group()
def cli() -> None:
    """Top Level CLI."""

@cli.command(
    short_help="s expressions",
    help="Applies s expressions to EO acquisitions",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
)
@click.option(
    "--input_reference",
    "-i",
    "input_reference",
    help="Input product reference",
    type=click.Path(),
    required=True,
)
@click.option(
    "--s-expression", "-s", "s_expression", help="s expression", required=True
)
@click.option("--cbn", "-b", "cbn", help="Common band name", required=True)
@click.option("--assets", "-a", "assets", help="Assets to Load", required=False, multiple=True)
@click.pass_context
def calculate(ctx, input_reference, s_expression, cbn, assets=None):

    dump(ctx)

    item = get_item(input_reference)

    logging.info(f"Processing {item.id}")
    if assets:
        logging.info(f"Assets: {assets}")

    try:
        os.mkdir(item.id)
    except FileExistsError:
        pass

    cbn = cbn.replace(" ", "-")

    result = os.path.join(item.id, f"{cbn}.tif")

    logging.info(f"Apply {s_expression} to {item.id}")

    apply_s_expression(item=item, s_expression=s_expression, out_tif=result, assets=assets)

    item_out = Item(
        id=item.id,
        geometry=item.geometry,
        bbox=item.bbox,
        datetime=item.datetime,
        properties=item.properties,
        stac_extensions=item.stac_extensions,
    )

    # eo_item = extensions.eo.EOItemExt(item_out)

    asset_properties = dict()

    asset_properties["s-expression"] = s_expression

    asset = Asset(
        href=os.path.basename(result),
        media_type=MediaType.COG,
        roles=["data"],
        extra_fields=asset_properties,
    )

    # eo_bands = [
    #    extensions.eo.Band.create(
    #        name=cbn.lower(),
    #        common_name=cbn.lower(),
    #        description=f"{cbn.lower()} ({s_expression})",
    #    )
    # ]

    # eo_item.set_bands(eo_bands, asset=asset)

    item_out.add_asset(key=cbn.lower(), asset=asset)

    cat = Catalog(id="catalog", description="s-expression")

    cat.add_items([item_out])

    cat.normalize_and_save(root_href="./", catalog_type=CatalogType.SELF_CONTAINED)

    logging.info("Done!")

@cli.command(
    help="Joins multiple STAC catalogs into a single catalog",
)
@click.option(
    "--stac_catalog_dir",
    "-d",
    type=click.Path(path_type=Path),
    multiple=True,
    required=True,
    help="Path to the STAC catalog directories (can be provided multiple times for multiple catalogs)",
)
@click.option(
    "--output_dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Path to the output directory - if not provided, defaults to 'stac-join' in the current working directory",
)
def join(stac_catalog_dir: list[Path], output_dir: Optional[Path] = None) -> None:
    logging.info("Joining STAC catalogs ...")
    logging.info(f"Input STAC catalog directories: {stac_catalog_dir}")
    logging.info(f"Output directory: {output_dir}")

    # Verify catalog.json exists
    for cat in stac_catalog_dir:
        if not (cat / "catalog.json").exists():
            msg = f"catalog.json does not exist under {cat.as_posix()}"
            raise ValueError(msg)

    output_dir = output_dir or Path.cwd() / "stac-join"
    output_dir.mkdir(exist_ok=True, parents=True)

    # Handle single catalog
    if len(stac_catalog_dir) == 1:
        logging.info("Single STAC catalog passed as input. Copying STAC directory to output directory")
        shutil.copytree(stac_catalog_dir[0], output_dir, dirs_exist_ok=True)
        return

    merge_stac_catalogs(
        stac_catalog_dirs=stac_catalog_dir,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    cli()
