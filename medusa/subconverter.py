import base64
import logging
from typing import List
from urllib.parse import ParseResult, unquote, parse_qs, urlparse, urlunparse


def b64decode_urlsafe(s: str) -> str:
    missing_padding = len(s) % 4
    if missing_padding != 0:
        s += "=" * (4 - missing_padding)
    return base64.urlsafe_b64decode(s).decode()


def handle_ss(ss: ParseResult):
    return "".join(
        (
            "forward=",
            ss.scheme,
            "://",
            ss.username,
            ":",
            ss.password,
            "@",
            ss.hostname,
            ":",
            str(ss.port),
            "#",
            unquote(ss.fragment),
        )
    )


def handle_trojan(tj: ParseResult):
    return "".join(
        (
            "forward=",
            tj.scheme,
            "://",
            tj.username,
            "@",
            tj.hostname,
            ":",
            str(tj.port),
            "?",
            f"serverName={parse_qs(tj.query).get('sni', tj.hostname)}",
            "&skipVerify=true",
            "#",
            unquote(tj.fragment),
        )
    )


class SubConverter:
    @staticmethod
    def dedup_urls(urls):
        deduped_urls = {}
        for url in urls:
            parsed_url = urlparse(url)
            url_without_fragment = urlunparse(
                (
                    parsed_url.scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    "",
                )
            )
            if (
                url_without_fragment not in deduped_urls
                or not deduped_urls[url_without_fragment]
            ):
                deduped_urls[url_without_fragment] = parsed_url.fragment
        final_urls = [
            url + ("#" + fragment if fragment else "")
            for url, fragment in deduped_urls.items()
        ]
        return final_urls

    @staticmethod
    def convert(backend: str, parse_results: List[ParseResult]):
        match backend:
            case "glider":
                return SubConverter._to_glider(parse_results)
            case _:
                raise NotImplementedError

    @staticmethod
    def _to_glider(parse_results: List[ParseResult]):
        res = list()
        for r in parse_results:
            logging.info(f"Preprocessing {r}")
            if r.scheme == "ss":
                if r.username is None:
                    netloc = b64decode_urlsafe(r.netloc)
                    r = urlparse(urlunparse(r).replace(r.netloc, netloc))
                if r.password is None:
                    username = b64decode_urlsafe(r.username)
                    r = urlparse(urlunparse(r).replace(r.username, username))
            logging.info(f"Handling {r}")
            pr = eval(f"handle_{r.scheme}")(r)
            logging.info(f"Constructed '{pr}'")
            res.append(pr)
        return SubConverter.dedup_urls(res)
