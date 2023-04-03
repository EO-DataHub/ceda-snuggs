import os
import sys
import logging
import click
from click2cwl import dump
import logging
from .s_expression import apply_s_expression
from .stac import get_item
from pystac import Item, Asset, MediaType, extensions, Catalog, CatalogType

logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


@click.command(
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
@click.pass_context
def main(ctx, input_reference, s_expression, cbn):

    dump(ctx)

    item = get_item(input_reference)

    logging.info(f"Processing {item.id}")

    try:
        os.mkdir(item.id)
    except FileExistsError:
        pass

    cbn = cbn.replace(" ", "-")

    result = os.path.join(item.id, f"{cbn}.tif")

    logging.info(f"Apply {s_expression} to {item.id}")

    apply_s_expression(item=item, s_expression=s_expression, out_tif=result)

    logging.info("STAC")

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

    logging.info("STAC")

    cat = Catalog(id="catalog", description="s-expression")

    cat.add_items([item_out])

    cat.normalize_and_save(root_href="./", catalog_type=CatalogType.SELF_CONTAINED)

    logging.info("Done!")


if __name__ == "__main__":
    main()
