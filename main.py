import json
from pprint import pprint
with open('addresses.json', 'r') as f:
    pprint(json.load(f))