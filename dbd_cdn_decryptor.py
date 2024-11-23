# Copyright 2024 Eigenvoid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import zlib

from Crypto.Cipher import AES

class DBDDecryption:
    ASSET_ENCRYPTION_PREFIX = 'DbdDAwAC'
    PROFILE_ENCRYPTION_PREFIX = 'DbdDAgAC'
    PROFILE_ENCRYPTION_AES_KEY = b'5BCC2D6A95D4DF04A005504E59A9B36E'
    ZLIB_COMPRESSION_PREFIX = 'DbdDAQEB'

    ACCESS_KEYS = {
        '8.3.0_qa': 'PMpWSDCacs4gxAsW5tIqRK6LdFXwYYIYYnPfevI1HQo=',
        '8.3.0_stage': 'tlr7va/WqYlQF2Yp+KQN7KDLtsG/jg7OpxB/pUCtrQA=',
        '8.3.0_cert': 'sQcyOnoA9/76i7I1Uv/9oXaxkjzMnI4Ec/hDsBSBIcA=',
        '8.3.0_ptb': '/ecXuJvk9l38ffnkHalYfeEbumocDBK+DaUeYcIr82o=',
        '8.3.0_live': 'fMYq7WF+cNspGeCujfjvuw0GxlpjsXwfhfsh6O2Xn9U=',
        '8.3.1_qa': 'AbVcU5Nd+lQs6LPYfBS9RgwXbaDX5mTE0LdWjABOZ+U=',
        '8.3.1_stage': '5MTApKAnan25Niya0Q4qGGC7B6lRLCx+eUS2bL3lT5c=',
        '8.3.1_cert': '4qLPWefFSxIkAJ8LwEKZKa+vqJ/GY102qOOFG5CUgA0=',
        '8.3.1_ptb': 'Krplg2UGkK+mWz179rwkJC/SqUCtj950NYP4yHgor0A=',
        '8.3.1_live': '2X/5Q6mVLlhiAvfndcpQGtiq0Ff6YbQihw+rXDSG0HE=',
        '8.3.2_qa': 'Q7togl29cDK8NzohvLOYZyfUwn9sDnFz2JzzAzM8lJk=',
        '8.3.2_stage': 'PBcq6dBi5lwreqEPQFtO0uhg3zJ5Sy/mKzojoKOtURI=',
        '8.3.2_cert': '6U8YeUkQAK/6SFU/apKdKWi4XQj6WpEYYr9oowegKns=',
        '8.3.2_ptb': 'HMx8ZiDyWQlJ4xBUkmLyYxjuOIitwB72mEmXhpRGVEs=',
        '8.3.2_live': 'Hqn3MOuoUmgV3tHEs+aGQ2h4okVd6VJeGnx7K+ltcGc=',
    }

    @staticmethod
    def decrypt_content(content, branch):
        if content.startswith(DBDDecryption.ASSET_ENCRYPTION_PREFIX):
            return DBDDecryption.decrypt_dbd_asset(content, branch)
        
        if content.startswith(DBDDecryption.PROFILE_ENCRYPTION_PREFIX):
            return DBDDecryption.decrypt_dbd_profile(content, branch)
        
        if content.startswith(DBDDecryption.ZLIB_COMPRESSION_PREFIX):
            return DBDDecryption.decompress_dbd_zlib(content, branch)
        
        if content and not DBDDecryption.is_valid_json(content):
            raise Exception('Decrypted data is not valid JSON. The access key might be incorrect, or the data could be corrupted.')
        
        return content
    
    @staticmethod
    def is_valid_json(input_string):
        if not input_string.strip():
            return True
        try:
            json.loads(input_string)
            return True
        except json.JSONDecodeError:
            return False

    @staticmethod
    def decrypt_dbd_asset(content, branch):
        if not content.startswith(DBDDecryption.ASSET_ENCRYPTION_PREFIX):
            raise Exception(f'Content does not start with {DBDDecryption.ASSET_ENCRYPTION_PREFIX}. Decryption cannot proceed.')
        
        payload = content[len(DBDDecryption.ASSET_ENCRYPTION_PREFIX):]
        raw_payload = base64.b64decode(payload)

        branch_length = len(branch)
        slice_length = 7 + branch_length
        key_id_buffer = raw_payload[:slice_length]
        key_id_buffer = bytes((byte + 1) % 256 for byte in key_id_buffer)

        cleaned_key_id = key_id_buffer.decode('ascii').replace('\u0001', '')
        access_key = DBDDecryption.ACCESS_KEYS.get(cleaned_key_id)
        if not access_key:
            raise Exception(f'The key ID "{cleaned_key_id}" does not exist in the list of available access keys.')
        
        decrypted_key = base64.b64decode(access_key)
        if not decrypted_key:
            raise Exception(f'Unknown AES key: "{cleaned_key_id}"')
        
        decoded_buffer = raw_payload[slice_length:]
        return DBDDecryption.process_decrypted_data(decoded_buffer, decrypted_key, branch)
    
    @staticmethod
    def decrypt_dbd_profile(content, branch):
        if not content.startswith(DBDDecryption.PROFILE_ENCRYPTION_PREFIX):
            raise Exception(f'Content does not start with {DBDDecryption.PROFILE_ENCRYPTION_PREFIX}. Decryption cannot proceed.')
        
        payload = content[len(DBDDecryption.PROFILE_ENCRYPTION_PREFIX):]
        raw_payload = base64.b64decode(payload)
        return DBDDecryption.process_decrypted_data(raw_payload, DBDDecryption.PROFILE_ENCRYPTION_AES_KEY, branch)
    
    @staticmethod
    def process_decrypted_data(buffer, encryption_key, branch):
        cipher = AES.new(encryption_key, AES.MODE_ECB)
        decrypted_buffer = cipher.decrypt(buffer)

        mutable_buffer = bytearray(decrypted_buffer)

        valid_non_padding_bytes = 0
        for i in range(len(mutable_buffer)):
            raw_byte_value = mutable_buffer[i]
            if raw_byte_value != 0:
                offset_byte_value = (raw_byte_value + 1) % 256
                mutable_buffer[i] = offset_byte_value
                valid_non_padding_bytes += 1
            else:
                break

        result_text = bytes(mutable_buffer[:valid_non_padding_bytes]).decode('ascii')
        return DBDDecryption.decrypt_content(result_text, branch)
    
    @staticmethod
    def decompress_dbd_zlib(content, branch):
        if not content.startswith(DBDDecryption.ZLIB_COMPRESSION_PREFIX):
            raise Exception(f'Content does not start with {DBDDecryption.ZLIB_COMPRESSION_PREFIX}. Decryption cannot proceed.')
        
        payload = content[len(DBDDecryption.ZLIB_COMPRESSION_PREFIX):]
        raw_payload = base64.b64decode(payload)

        if len(raw_payload) < 4:
            raise Exception('Raw payload is too short to contain deflated data.')
    
        expected_inflated_size = int.from_bytes(raw_payload[:4], byteorder='little')
        inflated_buffer = zlib.decompress(raw_payload[4:])

        if len(inflated_buffer) != expected_inflated_size:
            raise Exception(f'Inflated data size mismatch for content: expected {expected_inflated_size} bytes, but received {len(inflated_buffer)} bytes.')
        
        result_text = inflated_buffer.decode('utf-16')
        return DBDDecryption.decrypt_content(result_text, branch)
    
if __name__ == '__main__':
    encrypted_data = input('Enter the encrypted data: ')
    branch_input = input('Select a branch (q: QA, s: Stage, c: Cert, p: PTB, l: Live): ').lower()

    branch_map = {
        'q': 'qa',
        's': 'stage',
        'c': 'cert',
        'p': 'ptb',
        'l': 'live'
    }

    branch = branch_map.get(branch_input)
    if not branch:
        print('Invalid branch selection.')
    else:
        try:
            decrypted_data = DBDDecryption.decrypt_content(encrypted_data, branch)
            print(decrypted_data)
        except Exception as e:
            print('Error during decryption:', e)