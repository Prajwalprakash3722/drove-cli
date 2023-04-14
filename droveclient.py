import argparse
import configparser
import json
import os
import requests
import urllib3
from pathlib import Path
from requests.adapters import HTTPAdapter, Retry
from types import SimpleNamespace

class DroveException(Exception):
    """Exception raised while callign drove endpoint"""

    def __init__(self, status_code: int, message: str, raw: str = None):
        self.status_code = status_code
        self.raw = raw
        super().__init__(message)

class DroveClient:
    def __init__(self):
        self.endpoint: str = None
        self.auth_header: str = None
        self.insecure: bool = False
        self.session = requests.session()
        retries = Retry(connect=5,
                        read=5,
                        backoff_factor=0.1)

        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
    

    def start(self, endpoint: str = None, auth_header: str = None, insecure: bool = False):
        self.endpoint = endpoint
        self.auth_header = auth_header
        self.insecure = insecure
        self.session.verify = not insecure
        if insecure:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if auth_header:
            self.session.headers.update({"Authorization": auth_header})
        self.get("/apis/v1/ping")
        # print("Connection validated for endpoint: " + self.endpoint)        

    def get(self, path: str, expected_status = 200) -> dict:
        try:
            response = self.session.get(self.endpoint + path)
        except requests.ConnectionError as e:
            raise DroveException(-1, "Error connecting to endpoint " + self.endpoint, raw={})

        status_code = response.status_code
        text = response.text
        if status_code != expected_status:
            raise DroveException(status_code, "Drove call failed with status: " + str(status_code))
        api_response = None
        try:
            api_response = json.loads(text)
            # api_response = json.loads(text, object_hook=lambda d: SimpleNamespace(**d))
        except Exception as e:
            raise DroveException(status_code, str(e))
        if api_response["status"] != "SUCCESS":
            raise DroveException(status_code, message = api_response.get("message", ""), raw=text)
        return api_response["data"]

    def get_raw(self, path: str, expected_status: int = 200) -> dict:
        try:
            response = self.session.get(self.endpoint + path)
        except requests.ConnectionError as e:
            raise DroveException(-1, "Error connecting to endpoint " + self.endpoint, raw={})

        status_code = response.status_code
        text = response.text
        if status_code != expected_status:
            raise DroveException(status_code, "Drove call failed with status: " + str(status_code), raw=text)
        try:
            return json.loads(text)
        except Exception as e:
            raise DroveException(status_code, str(e))
    
    def get_to_file(self, path: str, filename: str, expected_status: int = 200) -> int:
        size = 0
        try:
            with self.session.get(self.endpoint + path, stream=True) as r:
                if r.status_code != expected_status:
                    raise DroveException(r.status_code, "Drove call failed with status: " + str(r.status_code))
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        #if chunk: 
                        f.write(chunk)
                        size = size + len(chunk)
            return size
        except DroveException:
            raise
        except Exception as e:
            raise DroveException(-1, str(e))
        
def build_drove_client(drove_client: DroveClient, args: SimpleNamespace):
    endpoint = args.endpoint
    auth_header = args.auth_header
    insecure = args.insecure

    # If cmdl options are not passed, see if config file is passed
    if endpoint is None:
        config_file = args.config
        # If config file path is not passed, see if .drove exists in home and use that
        if config_file == None:
            config_file = str(Path.home()) + "/.drove"
        
        # Try to parse config if it exists
        if os.path.isfile(config_file):
            config_parser = configparser.ConfigParser()
            try:
                config_parser.read(config_file)
                drove_config = config_parser["drove"]
                endpoint = drove_config["endpoint"]
                auth_header = drove_config.get("auth_header", None)
                insecure = drove_config.get("insecure", False)
            except Exception as e:
                #Looks like some random file was passed. Bail out
                print("Error parsing config file " + config_file + ": " + str(e))
                return None

    # At least endpoint is needed
    if endpoint == None:
        print("error: provide config file or required command line params for drove connectivity\n")
        return None
    drove_client.start(endpoint, auth_header, insecure)
    return drove_client
    