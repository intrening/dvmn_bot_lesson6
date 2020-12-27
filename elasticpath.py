import requests
import os
from datetime import timedelta, datetime


EP_ACCESS_TOKEN = EP_TOKEN_TIME = None


def fetch_products():
    url = 'https://api.moltin.com/v2/products'
    headers = {'Authorization': f'Bearer {get_ep_access_token()}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_image_url(id):
    url = f'https://api.moltin.com/v2/files/{id}'
    headers = {'Authorization': f'Bearer {get_ep_access_token()}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']['link']['href']


def get_product(product_id):
    url = f'https://api.moltin.com/v2/products/{product_id}'
    headers = {'Authorization': f'Bearer {get_ep_access_token()}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_ep_access_token():
    global EP_ACCESS_TOKEN
    global EP_TOKEN_TIME

    if not EP_ACCESS_TOKEN or datetime.now() > EP_TOKEN_TIME + timedelta(hours=1):
        url = 'https://api.moltin.com/oauth/access_token'
        payload = {
            'grant_type': 'client_credentials',
            'client_secret': os.environ.get('EP_CLIENT_SECRET'),
            'client_id': os.environ.get('EP_CLIENT_ID'),
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
        EP_ACCESS_TOKEN = response.json()['access_token']
        EP_TOKEN_TIME = datetime.now()
    return EP_ACCESS_TOKEN


def add_to_cart(product_id, quantity, chat_id):
    url = f'https://api.moltin.com/v2/carts/:{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
        'Content-Type': 'application/json',
    }
    payload = {
        'data': {
            'id': product_id,
            'quantity': int(quantity),
            'type': 'cart_item',
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()


def remove_from_cart(product_id, chat_id):
    url = f'https://api.moltin.com/v2/carts/:{chat_id}/items/{product_id}'
    headers = {'Authorization': f'Bearer {get_ep_access_token()}', }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()


def get_carts_products(chat_id):
    url = f'https://api.moltin.com/v2/carts/:{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()['data']


def get_total_price(chat_id):
    url = f'https://api.moltin.com/v2/carts/:{chat_id}'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']['meta']['display_price']['with_tax']['formatted']


def create_customer(name, email):
    url = 'https://api.moltin.com/v2/customers/'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    payload = {
        'data': {
            'type': 'customer',
            'name': name,
            'email': email,
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()


def create_product(name, slug, sku, description, amount, currency='RUB', manage_stock=False, includes_tax=True, status='live', commodity_type='physical'):
    url = 'https://api.moltin.com/v2/products'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    payload = {
        'data': {
            'type': 'product',
            'name': name,
            'slug': slug,
            'sku': sku,
            'manage_stock': manage_stock,
            'description': description,
            'price': [
                {
                    'amount': amount,
                    'currency': currency,
                    'includes_tax': includes_tax,
                }
            ],
            'status': 'live',
            'commodity_type': commodity_type,
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['data']['id']


def create_file(file_url, public=True):
    response = requests.get(file_url)
    response.raise_for_status()
    filename = file_url.split('/')[-1]
    with open(filename, 'wb') as f:
        f.write(response.content)
    url = 'https://api.moltin.com/v2/files'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    files = {
        'file': (filename, open(filename, 'rb')),
        'public': (None, 'true'),
    }
    response = requests.post(url, files=files, headers=headers)
    response.raise_for_status()
    os.remove(filename)
    return response.json()['data']['id']


def create_relationships(product_id, file_id):
    url = f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    payload = {
        'data': {
            'type': 'main_image',
            'id': file_id,
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()


def create_flow(name, slug, description, enabled=True):
    url = 'https://api.moltin.com/v2/flows'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    payload = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': slug,
            'description': description,
            'enabled': enabled,
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['data']['id']


def create_field(name, slug, field_type, description, required, enabled, flow_id):
    url = 'https://api.moltin.com/v2/fields'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    payload = {
        'data': {
            'type': 'field',
            'name': name,
            'slug': slug,
            'field_type': field_type,
            'description': description,
            'required': required,
            'enabled': enabled,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    }
                }
            }
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['data']['id']


def create_entry(flow_slug, data):
    data['type'] = 'entry'
    url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    payload = {
        'data': data,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['data']['id']


def update_entry(flow_slug, entry_id, data):
    url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    data['type'] = 'entry'
    data['id'] = 'entryID'
    payload = {
        'data': data,
    }
    response = requests.put(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['data']['id']


def get_entries(flow_slug):
    url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries'
    headers = {
        'Authorization': f'Bearer {get_ep_access_token()}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


# for pizzeria in get_entries('pizzeria'):
#     update_entry('pizzeria', pizzeria['id'], data={
#         'deliver_telegram_id': '36638324',
#     })
