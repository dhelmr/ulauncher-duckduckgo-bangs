import sys
import json
from tempfile import NamedTemporaryFile
import urllib.request
from urllib.parse import quote
import os.path


URL_PLACEHOLDER = "{{{s}}}"
DEFAULT_BANGS_URL = "https://duckduckgo.com/bang.js"


class DBang:
    category: str
    subcategory: str
    domain: str
    url: str
    site: str
    r: int
    t: str

    def __init__(self, category, subcategory, domain, url, site, r, t):
        self.category = category
        self.subcategory = subcategory
        self.domain = domain
        self.url = url
        self.site = site
        self.r = r
        self.t = t

    def get_url(self, term):
        return self.url.replace(URL_PLACEHOLDER, quote(term, safe="/"))


class DBangs:
    def __init__(self, js_file=None, bangs=None):
        if js_file is not None:
            self.load_from_file(js_file)

    def load_from_file(self, js_file) -> None:
        with open(js_file, "r",  encoding='utf-8') as file:
            data = file.read()

        def map_json(entry):
            return DBang(category=entry.get("c", ""),
                         subcategory=entry.get("sc", ""),
                         domain=entry.get("d", ""),
                         url=entry.get("u", ""),
                         t=entry.get("t", ""),
                         site=entry.get("s", ""),
                         r=entry.get("r", 0))

        obj = json.loads(data)
        if type(obj) is not list:
            raise("Unexpected type of json data", type(obj))
        bangs = [map_json(entry) for entry in obj]
        self._set_bangs(bangs)

    def _set_bangs(self, bangs):
        self.bangs = bangs
        self._by_terms = dict()
        for bang in self.bangs:
            self._by_terms[bang.t] = bang

    def match_exactly(self, bang_term: str) -> DBang:
        return self._by_terms.get(bang_term, None)

    def search(self, contains: list) -> list:
        u_contains = [s.upper() for s in contains]

        def filter_bang_entry(bang):
            for term in u_contains:
                if term not in bang.site.upper() and term not in bang.domain.upper() and term not in bang.t.upper():
                    return False
            return True
        filteredBangs = filter(filter_bang_entry, self.bangs)
        orderedBangs = sorted(
            filteredBangs, key=lambda entry: entry.r, reverse=True)
        return orderedBangs

    def __iter__(self):
        return iter(self.bangs)


class BangsManager:
    def __init__(self, storage_path="./.bangs-cache"):
        self.storage_path = storage_path

    def download(self, url, destination):
        urllib.request.urlretrieve(url, destination)

    def download_latest_bangs(self, url=DEFAULT_BANGS_URL, destination=None):
        if destination is None:
            destination = self._make_latest_file()
        self.download(url, destination)
        return destination

    def _make_latest_file(self):
        return os.path.join(self.storage_path, "bang.js")

    def get_latest(self, force_download=False):
        latest_file_path = self._make_latest_file()
        if force_download or not os.path.exists(latest_file_path):
            self.download_latest_bangs()
        return DBangs(latest_file_path)
