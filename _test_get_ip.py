# -*- coding: utf-8 -*-
import requests
import json

if __name__ == '__main__':
    r = requests.get('http://127.0.0.1:7777/ip')
    print r.content
