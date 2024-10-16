import os
import base64
import requests
import datetime
from dotenv import load_dotenv

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

# Load environment variables from the .env file
load_dotenv()

BASE_URL = os.getenv("KALSHI_BASE_URL")


class KalshiAPI:
    def __init__(self):
        # Load secrets from environment variables
        self.private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH")
        self.access_key = os.getenv("KALSHI_ACCESS_KEY")

        # Ensure required variables are set
        if not self.private_key_path or not self.access_key:
            raise ValueError("Required environment variables are not set")

        # Load private key from file
        self.private_key = self.load_private_key_from_file(self.private_key_path)

    def load_private_key_from_file(self, file_path: str) -> rsa.RSAPrivateKey:
        with open(file_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )

        return private_key

    def sign_pss_text(self, private_key: rsa.RSAPrivateKey, text: str):
        # Before signing, we need to hash our message.
        # The hash is what we actually sign.
        # Convert the text to bytes
        message = text.encode("utf-8")

        try:
            signature = private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode("utf-8")
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e

    def get_timestamp_in_milliseconds(self):
        # Get the current time
        current_time = datetime.datetime.now()
        # Convert the time to a timestamp (seconds since the epoch)
        timestamp = current_time.timestamp()
        # Convert the timestamp to milliseconds
        return int(timestamp * 1000)

    def create_headers(self, method, path):
        """
        Create the headers needed for API requests.

        :param method: The HTTP method being used, e.g. "GET".
        :param path: The API path being accessed. :return: Dictionary containing the necessary headers.
        """
        # Get the current timestamp in milliseconds
        timestampt_str = str(self.get_timestamp_in_milliseconds())

        # Construct the message to sign
        msg_string = timestampt_str + method + path

        # Sign the message
        sig = self.sign_pss_text(self.private_key, msg_string)

        # Return the headers
        headers = {
            "KALSHI-ACCESS-KEY": self.access_key,
            "KALSHI-ACCESS-SIGNATURE": sig,
            "KALSHI-ACCESS-TIMESTAMP": timestampt_str,
        }

        return headers

    def login(self):
        """
        Logs in to retrieve session member_id and token. Uses API key.
        """
        method = "POST"
        path = "/trade-api/v2/login"

        headers = self.create_headers(method, path)

        assert BASE_URL is not None
        response = requests.post(BASE_URL + path, headers=headers)

        return response.json()

    def websocket_auth_headers(self):
        """
        UNDOCUMENTED!

        This was found in the Kalshi #dev Discord channel:

        > "You have to use "GET" as the method and "/trade-api/ws/v2" as the path when building the string that gets hashed and signed."
        """
        method = "GET"
        path = "/trade-api/ws/v2"

        headers = self.create_headers(method, path)

        return headers

    def get_balance(self):
        """
        Example method that calls the balance endpoint using the headers.
        """
        method = "GET"
        path = "/trade-api/v2/portfolio/balance"

        # Generate the headers using the method and path
        headers = self.create_headers(method, path)

        # Make the request
        assert BASE_URL is not None
        response = requests.get(BASE_URL + path, headers=headers)

        # Output the response
        print("Status Code:", response.status_code)
        print("Response Body:", response.text)
