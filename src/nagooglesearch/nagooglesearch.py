#!/usr/bin/env python3

import bot_safe_agents, dataclasses, datetime, enum, json, random, re, requests, time, urllib.parse

from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

def get_all_user_agents() -> list[str]:
	"""
	Get a list of user agents.
	"""
	return bot_safe_agents.get_all()

def get_random_user_agent() -> str:
	"""
	Get a random user agent.
	"""
	return bot_safe_agents.get_random()

def get_tbs(date_from: datetime.datetime = None, date_to: datetime.datetime = None):
	"""
	Get a value for the 'to be searched' Google query parameter.
	"""
	date_format = "%m/%d/%Y"
	date_from = date_from.strftime(date_format) if date_from else ""
	date_to = date_to.strftime(date_format) if date_to else ""
	return f"cdr:1,cd_min:{date_from},cd_max:{date_to}"

class Error(enum.Enum):
	"""
	Enum containing various error states.
	"""
	REQUESTS = "REQUESTS_EXCEPTION"
	RATE_LIMIT = "429_TOO_MANY_REQUESTS"

@dataclasses.dataclass
class GooglePagination:
	"""
	Class for storing Google pagination details.
	"""
	start: int = 0
	num: int = 10

@dataclasses.dataclass
class GoogleURLs:
	"""
	Class for storing Google URLs.
	"""
	homepage: str = ""
	homepage_search: str = ""
	search: str = ""

class GoogleClient:

	def __init__(
		self,
		tld: str = "com",
		homepage_parameters: dict[str, str] = {
			"btnK": "Google+Search",
			"source": "hp"
		},
		search_parameters: dict[str, str] = {
		},
		user_agent: str = "",
		proxy: str = "",
		max_results: int = 100,
		min_sleep: int = 8,
		max_sleep: int = 18,
		debug: bool = False
	):
		"""
		Class for Google searching.
		"""
		self.__tld: str = tld.lower()
		self.__homepage_parameters: dict[str, str] = homepage_parameters
		self.__search_parameters: dict[str, str] = search_parameters
		self.__pagination: GooglePagination = self.__get_pagination()
		self.__urls: GoogleURLs = self.__get_urls()
		self.__headers: dict[str, str] = self.__get_headers(user_agent)
		self.__cookies: dict[str, str] = self.__get_cookies()
		self.__proxies: dict[str, str] = self.__get_proxies(proxy)
		self.__max_results: int = max_results
		self.__min_sleep: int = min_sleep
		self.__max_sleep: int = max_sleep
		self.__debug: bool = debug
		self.__session: requests.Session = None
		self.__error: Error = None

	def get_error(self):
		"""
		Get the current error, if any.
		"""
		return self.__error.value if self.__error else ""

	def __jdump(self, data: list[str] | dict[str, str]):
		"""
		Serialize a data to a JSON string.
		"""
		return json.dumps(data, indent = 4, ensure_ascii = False)

	def __print_debug(self, heading: str, text: int | str | list[str] | dict[str, str]):
		"""
		Print a debug information.
		"""
		if self.__debug:
			if isinstance(text, (list, dict)):
				text = self.__jdump(text)
			print(f"{heading}: {text}")

	def __get_pagination(self):
		"""
		Get Google pagination details.
		"""
		pagination = GooglePagination()
		if "start" in self.__search_parameters:
			pagination.start = int(self.__search_parameters["start"])
			self.__search_parameters.pop("start")
		if "num" in self.__search_parameters:
			pagination.num = int(self.__search_parameters["num"])
			if pagination.num == 10:
				self.__search_parameters.pop("num")
		return pagination

	def __get_urls(self):
		"""
		Get Google URLs.
		"""
		urls = GoogleURLs()
		urls.homepage = self.__get_url()
		urls.homepage_search = self.__get_url("/search", self.__homepage_parameters | self.__search_parameters)
		urls.search = self.__get_url("/search", self.__search_parameters)
		return urls

	def __get_url(self, path: str = "/", search_parameters: dict[str, str] = None) -> str:
		"""
		Get a Google URL.
		"""
		search_parameters = urllib.parse.urlencode(search_parameters, doseq = True) if search_parameters else ""
		return urllib.parse.urlunsplit(("https", f"www.google.{self.__tld}", path, search_parameters, ""))

	def __get_paginated_search_url(self):
		"""
		Get a paginated Google search URL.
		"""
		url = self.__urls.homepage_search
		if self.__pagination.start > 0:
			sep = "&" if self.__search_parameters else "?"
			url = f"{self.__urls.search}{sep}start={self.__pagination.start}"
		self.__pagination.start += self.__pagination.num
		return url

	def __get_headers(self, user_agent: str = ""):
		"""
		Get HTTP request headers.
		"""
		if not user_agent:
			user_agent = get_random_user_agent()
		return {
			"User-Agent": user_agent,
			"Accept-Language": "en-US, *",
			"Accept": "*/*",
			"Referer": self.__urls.homepage,
			"Upgrade-Insecure-Requests": "1"
		}

	def __get_cookies(self):
		"""
		Get HTTP cookies.\n
		This is a new cookie consent mechanism.\n
		The 'SOCS' cookie rejects all tracking and is valid for 13 months, created on 2024-09-23.
		"""
		return {
			"SOCS": "CAESHAgCEhJnd3NfMjAyNDA5MjMtMF9SQzEaAmRlIAEaBgiApc23Bg"
		}

	def __update_consent_cookie(self):
		"""
		Update the 'CONSENT' HTTP cookie.\n
		This is an old cookie consent mechanism.
		"""
		cookies = self.__session.cookies.get_dict()
		key = "CONSENT"
		if key in cookies and isinstance(cookies[key], str) and re.search(r"PENDING\+[\d]+", cookies[key], re.IGNORECASE):
			self.__print_debug("Info", f"Looks like your IP address is originating from an EU location. Your search results may vary. Attempting to work around this by updating the '{key}' cookie...")
			today = datetime.date.today().strftime("%Y%m%d")
			id = cookies[key].split("+", 1)[-1]
			cookies[key] = f"YES+shp.gws-{today}-0-RC1.en+FX+{id}"
			self.__print_debug("Updated Cookies", cookies)
			self.__session.cookies.clear()
			self.__session.cookies.update(cookies)

	def __get_proxies(self, proxy: str = "") -> dict[str, str]:
		"""
		Get HTTP proxies.
		"""
		proxies = {}
		if proxy:
			proxies["http"] = proxies["https"] = urllib.parse.urlsplit(proxy).geturl()
		return proxies

	def __sleep_random(self):
		"""
		Sleep for a random amount of time in seconds.
		"""
		sleep = random.randint(self.__min_sleep, self.__max_sleep)
		if sleep > 0:
			time.sleep(sleep)

	def __get_page(self, url: str):
		"""
		Send an HTTP GET request and return the HTML content of the response.
		"""
		self.__print_debug("Request URL", url)
		html = ""
		response = None
		try:
			response = self.__session.get(url, headers = self.__headers, verify = False, allow_redirects = True, timeout = 30)
			self.__print_debug("Response Status Code", response.status_code)
			if response.status_code == 200:
				html = response.text
			elif response.status_code == 429:
				self.__error = Error.RATE_LIMIT
		except (requests.exceptions.RequestException, requests.packages.urllib3.exceptions.HTTPError) as ex:
			self.__error = Error.REQUESTS
			self.__print_debug("Exception", str(ex))
		finally:
			if response:
				response.close()
		return html

	def __extract_links(self, html: str) -> list[str]:
		"""
		Extract links (URLs) from an HTML content.
		"""
		links = []
		soup = BeautifulSoup(html, "html.parser")
		search = soup.find(id = "search")
		if search:
			links = search.find_all("a", href = True)
		else:
			for id in ["gbar", "top_nav", "searchform"]:
				element = soup.find(id = id)
				if element:
					element.clear()
			links = soup.find_all("a", href = True)
		return [link["href"] for link in links]

	def __validate_link(self, link: str) -> str:
		"""
		Validate a link (URL).
		"""
		tmp = ""
		url = urllib.parse.urlsplit(link)
		scheme = url.scheme.lower()
		domain = url.netloc.lower()
		if domain and "google" not in domain:
			if scheme and "google" not in scheme and not domain.endswith("goo.gl"):
				tmp = url.geturl()
		else:
			query_string = urllib.parse.parse_qs(url.query)
			for key, value in query_string.items():
				if key in ["q", "u", "link"] and value:
					tmp = self.__validate_link(value[0])
					break
		return tmp

	def search(self) -> list[str]:
		"""
		Start a Google search.
		"""
		results = set()
		self.__error = None
		self.__print_debug("Initial Headers", self.__headers)
		self.__print_debug("Initial Cookies", self.__cookies)
		self.__print_debug("Initial Proxies", self.__proxies)
		self.__session = requests.Session()
		self.__session.cookies.update(self.__cookies)
		self.__session.proxies = self.__proxies
		self.__session.max_redirects = 10
		self.__get_page(self.__urls.homepage)
		if not self.__error:
			self.__update_consent_cookie()
			while True:
				self.__sleep_random()
				html = self.__get_page(self.__get_paginated_search_url())
				if self.__error or not html:
					break
				found = False
				for link in self.__extract_links(html):
					# self.__print_debug("Link", link)
					link = self.__validate_link(link)
					if link:
						found = True
						results.add(link)
				if not found or len(results) >= self.__max_results:
					break
			results = sorted(results, key = str.casefold)
		self.__session.close()
		results = list(results)
		# self.__print_debug("Results", results)
		return results
