import argparse
import logging
import base64
from functools import reduce
from typing import List

import requests
from urllib.parse import urlparse, ParseResult

from medusa.config import config, template
from medusa.subconverter import SubConverter, b64decode_urlsafe


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] - %(message)s - [%(filename)s:%(lineno)d]",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def fetch_config(url: str) -> List[ParseResult]:
    logging.info(f"Handling subscription {url}")
    
    def try_fetch_url(test_url: str) -> requests.Response:
        # Simulate browser request with proper headers
        # Note: We don't include Accept-Encoding to avoid compression issues with base64 content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(test_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response
    
    try:
        # First try the original URL
        response = try_fetch_url(url)
        
        # Check if response contains error message suggesting to use flag
        if "flag=ss" in response.text and not any(response.text.startswith(scheme) for scheme in ['ss://', 'trojan://', 'vmess://', 'vless://']):
            logging.info(f"Original URL returned error message, trying with &flag=ss")
            # Try with flag parameter
            flag_url = url + ("&flag=ss" if "?" in url else "?flag=ss")
            response = try_fetch_url(flag_url)
            logging.info(f"Successfully fetched with flag parameter")
        
    except requests.RequestException as e:
        logging.error(f"Failed to fetch subscription from {url}: {e}")
        return []
    
    try:
        
        # Try different decoding methods
        hosts = []
        
        # Method 1: Standard base64 decoding
        try:
            hosts = base64.b64decode(response.content).decode().splitlines(keepends=False)
            logging.info(f"Successfully decoded using standard base64")
        except Exception as e1:
            logging.info(f"Standard base64 failed: {e1}")
            
            # Method 2: URL-safe base64 with padding correction
            try:
                hosts = b64decode_urlsafe(response.content.decode()).splitlines(keepends=False)
                logging.info(f"Successfully decoded using URL-safe base64 with padding")
            except Exception as e2:
                logging.info(f"URL-safe base64 failed: {e2}")
                
                # Method 3: Check if response is already plain text (not base64)
                try:
                    text_content = response.text
                    if any(text_content.startswith(scheme) for scheme in ['ss://', 'trojan://', 'vmess://', 'vless://']):
                        hosts = text_content.splitlines(keepends=False)
                        logging.info(f"Successfully processed as plain text")
                    else:
                        logging.warning(f"Response doesn't appear to be valid subscription data: {text_content[:100]}")
                        return []
                except Exception as e3:
                    logging.error(f"All decoding methods failed: {e3}")
                    return []
        
        if hosts and len(hosts) > 0:
            print(hosts[0])
            return [urlparse(host) for host in hosts if len(host) and any(host.startswith(scheme) for scheme in ['ss://', 'trojan://', 'vmess://', 'vless://'])]
        else:
            logging.warning(f"No valid hosts found in response from {url}")
            return []
            
    except Exception as e:
        logging.error(f"Unexpected error processing {url}: {e}")
        return []


def main():
    setup_logger()
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=str, required=True)
    parser.add_argument("--backend", type=str, required=False, default="glider")
    args = parser.parse_args()
    pr_list = list()
    for url in config()["subscriptions"]:
        results = fetch_config(url)
        if results:  # Only process if we got valid results
            converted = SubConverter.convert(args.backend, results)
            if converted:  # Only add if conversion was successful
                pr_list.append(converted)
        else:
            logging.warning(f"Skipping URL {url} - no valid results")

    if pr_list:
        result = list(map(lambda e: f"{e}\n", reduce(list.__add__, pr_list)))
        with open(args.output, "w") as f:
            content = template(args.backend)
            f.writelines(content)
            f.writelines(result)
        logging.info(f"Successfully wrote {len(result)} entries to {args.output}")
    else:
        logging.error("No valid subscription data found from any URL")
        # Still create the file with just the template
        with open(args.output, "w") as f:
            content = template(args.backend)
            f.writelines(content)
        logging.info(f"Created {args.output} with template only")
    return


if __name__ == "__main__":
    exit(main())
