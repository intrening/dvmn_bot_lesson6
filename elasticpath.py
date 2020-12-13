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
        client_id = os.environ.get('EP_CLIENT_ID')
        url = 'https://api.moltin.com/oauth/access_token'
        payload = {
            'client_id': client_id,
            'grant_type': 'implicit',
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
