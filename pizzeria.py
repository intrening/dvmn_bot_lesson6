import json
import slugify
from elasticpath import (
    create_product, create_file, create_relationships,
    create_entry,
)


def create_products(json_filename):
    with open(json_filename, 'r') as f:
        menu = json.load(f)

    for menu_item in menu:
        product_id = create_product(
            name=menu_item['name'],
            slug=slugify.slugify(menu_item["name"]),
            sku=str(menu_item['id']),
            description=menu_item['description'],
            amount=menu_item['price'],
        )
        file_id = create_file(file_url=menu_item['product_image']['url'])
        create_relationships(product_id, file_id)


def create_pizzerias(json_filename):
    with open(json_filename, 'r') as f:
        pizzerias = json.load(f)

    for pizzeria in pizzerias:
        create_entry(
            flow_slug='pizzeria',
            address=pizzeria['address']['full'],
            alias=pizzeria['alias'],
            longitude=pizzeria['coordinates']['lon'],
            latitude=pizzeria['coordinates']['lat'],
        )
