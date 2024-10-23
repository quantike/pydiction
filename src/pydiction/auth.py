import base64
import requests
import datetime
from dotenv import load_dotenv

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

from pydiction.state import State

# Load environment variables from the .env file
load_dotenv()


class Authenticator:
    def __init__(self, state: State):
        self.state = state

        # raise error if state doesn't have the key path
        if self.state.private_key_path is None:
            raise ValueError("Missing PRIVATE_KEY_PATH from State")

        self.private_key = self._load_private_key_from_file(self.state.private_key_path)

    def _load_private_key_from_file(self, file_path: str) -> rsa.RSAPrivateKey:
        """
        Loads the private key from the KALSHI_PRIVATE_KEY_PATH (which should be in your .env).

        NOTE: This was ripped from the Kalshi example: <https://trading-api.readme.io/reference/api-keys>
        """
        with open(file_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )

        return private_key

    def _sign_pss_text(self, private_key: rsa.RSAPrivateKey, text: str):
        """
        Hashes our text, then signs that hash, and finally converts it to bytes.

        NOTE: This was ripped from the Kalshi example: <https://trading-api.readme.io/reference/api-keys>
        """
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

    def _get_timestamp_in_milliseconds(self):
        """
        Gets the timestamp in milliseconds.

        NOTE: This was ripped from the Kalshi example: <https://trading-api.readme.io/reference/api-keys>
        """
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
        :param path: The API path being accessed.

        :return: Dictionary containing the necessary headers.
        """
        # Get the current timestamp in milliseconds
        timestampt_str = str(self._get_timestamp_in_milliseconds())

        # Construct the message to sign
        msg_string = timestampt_str + method + path

        # Sign the message
        sig = self._sign_pss_text(self.private_key, msg_string)

        # Return the headers
        headers = {
            "KALSHI-ACCESS-KEY": str(self.state.access_key),
            "KALSHI-ACCESS-SIGNATURE": str(sig),
            "KALSHI-ACCESS-TIMESTAMP": str(timestampt_str),
        }

        return headers

    def get_auth_headers_rest(self, base_url: str):
        """
        Logs in to retrieve session member_id and token. Uses API key.

        :param base_url (str): The base URL for the REST endpoint. Dependent on `exchange` from `State`.
        """
        method = "POST"
        path = "/trade-api/v2/login"

        additional_headers = {
            "email": self.state.email,
            "password": self.state.password,
        }

        headers = self.create_headers(method, path) | additional_headers

        response = requests.post(base_url + path, headers=headers)

        return response.json()

    def get_auth_headers_ws(self):
        """
        UNDOCUMENTED!

        This was found in the Kalshi #dev Discord channel:

        > "You have to use "GET" as the method and "/trade-api/ws/v2" as the path when building the string that gets hashed and signed."
        """
        method = "GET"
        path = "/trade-api/ws/v2"  # weirdly, this requires a bit more than the path

        headers = self.create_headers(method, path)

        return headers
