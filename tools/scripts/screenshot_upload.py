#!/usr/bin/env python

import argparse
import os
from base64 import b64encode

import requests

from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE

ANON_UPLOAD_ID = 'ce8c41d2c1a72d1'


def is_dir(dirname):
    if not os.path.isdir(dirname):
        msg = f'{dirname} is not a directory'
        raise argparse.ArgumentTypeError(msg)
    else:
        return os.path.abspath(os.path.realpath(os.path.expanduser(dirname)))


def upload(path: str, headers: dict):
    print(f'Uploading {path}')
    with open(path, 'rb') as image_file:
        binary_data = image_file.read()
        image = b64encode(binary_data)

    data = {
        'image': image,
    }
    response = requests.post(
        url='https://api.imgur.com/3/upload',
        data=data,
        headers=headers,
        timeout=DEFAULT_TIMEOUT_TUPLE,
    )
    print(response.status_code)

    if response.ok:
        json = response.json()
        data = json['data']
        link = data['link']
        delete_hash = data['deletehash']
        print(f'file: {path} was successfully upload to imgur: {link} -- dh: {delete_hash}')
    else:
        print(f'uploading {path} failed with status code {response.status_code}')


def main(directory: str):
    files = [os.path.join(directory, file) for file in os.listdir(directory)]

    if not files:
        print('No screenshots to upload')
        exit(0)

    headers = {'Authorization': f'Client-ID {ANON_UPLOAD_ID}'}

    for path in files:
        upload(path, headers)
    exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Uploads screenshots to imgur')
    parser.add_argument(
        'directory',
        help='The directory containing the failure screenshots',
        type=is_dir,
    )
    args = parser.parse_args()
    main(args.directory)
