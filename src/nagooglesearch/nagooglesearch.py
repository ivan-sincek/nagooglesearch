#!/usr/bin/env python3

import bot_safe_agents, dataclasses, datetime, enum, json, random, re, requests, time, urllib.parse, urllib3

from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_all_user_agents():
	"""
	Get a list of user agents.
	"""
	return bot_safe_agents.get_all()

def get_random_user_agent():
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
	REQUEST = "REQUEST_EXCEPTION"
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
	homepage: str
	homepage_search: str
	search: str

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
		cookies: dict[str, str] = {
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
		self.__headers: dict[str, str] = self.__get_default_headers(user_agent)
		self.__cookies: dict[str, str] = self.__get_default_cookies() if not cookies else cookies
		self.__proxy: str = self.__get_proxy(proxy)
		self.__max_results: int = max_results
		self.__min_sleep: int = min_sleep
		self.__max_sleep: int = max_sleep
		self.__debug: bool = debug
		self.__error: Error = None

	def get_error(self) -> (Error | None):
		"""
		Get the current error, if any.
		"""
		return self.__error

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
		if "num" in self.__search_parameters: # deprecated
			pagination.num = int(self.__search_parameters["num"])
			if pagination.num >= 10:
				pagination.num = 10
				self.__search_parameters.pop("num")
		return pagination

	def __get_urls(self):
		"""
		Get Google URLs.
		"""
		return GoogleURLs(
			homepage = self.__get_url(),
			homepage_search = self.__get_url("/search", self.__homepage_parameters | self.__search_parameters),
			search = self.__get_url("/search", self.__search_parameters)
		)

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

	def __get_default_headers(self, user_agent: str = ""):
		"""
		Get default HTTP request headers.
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

	def __get_default_cookies(self):
		"""
		Get default HTTP cookies.\n
		This is a newer cookie consent mechanism.\n
		The below 'SOCS' and '__Secure-ENID' cookies reject all tracking and are valid for 13 months, created on 2026-03-20, but likely no longer work.
		More at: https://policies.google.com/technologies/cookies/embedded?hl=en-US
		"""
		return {
			"SOCS": "CAESHAgBEhJnd3NfMjAyNjAzMTgtMF9SQzEaAmRlIAEaBgiAnPLNBg",
			"__Secure-ENID": "32.SE=gBjbwa3RV0i1brALmGVI3rQ6ch-rqr6gH0NWaiITdV3_idyh6rX9yDJDePENSGmqM3VktRUwwGLuthhL6XsjoA4zX2kR0FsZyCBDjn689FPvuue7plDPey9pEUogNttvSUt7gVfYfl8XL6_0ntYRqGZkyzUSGQjR5h87zWXRy-3q4zmJeR0wcyNOfvJpniWoXZyB3a7JBFasgglVA3v6DclVvYmH7Esa8KnZbZ-mK3HxciG0pAqcucejfG1fyF19t9e95vGlaHT6-ZXwfEYhCxxgpptiTxQyuzUlAziTpsi3CXTdxOk"
		}

	def __update_consent_cookie(self, session: requests.Session):
		"""
		Update the 'CONSENT' HTTP cookie.\n
		This is an older cookie consent mechanism.
		"""
		cookies = session.cookies.get_dict()
		key = "CONSENT"
		if key in cookies and isinstance(cookies[key], str) and re.search(r"PENDING\+[\d]+", cookies[key], re.IGNORECASE):
			self.__print_debug("Info", f"Looks like your IP address is originating from an EU location. Your search results may vary. Attempting to work around this by updating the '{key}' cookie...")
			today = datetime.date.today().strftime("%Y%m%d")
			id = cookies[key].split("+", 1)[-1]
			cookies[key] = f"YES+shp.gws-{today}-0-RC1.en+FX+{id}"
			self.__print_debug(f"Updated '{key}' cookie", cookies[key])
			session.cookies.clear()
			session.cookies.update(cookies)

	def __get_proxy(self, proxy: str):
		"""
		Get an HTTP proxy.
		"""
		if proxy:
			proxy = urllib.parse.urlsplit(proxy).geturl()
		return proxy

	def __sleep_random(self):
		"""
		Sleep for a random amount of time in seconds.
		"""
		sleep = random.randint(self.__min_sleep, self.__max_sleep)
		if sleep > 0:
			time.sleep(sleep)

	def __get_page(self, session: requests.Session, url: str):
		"""
		Send an HTTP GET request and return the HTML content of the response.
		"""
		self.__print_debug("Request URL", url)
		html = ""
		response = None
		try:
			response = session.get(url, headers = self.__headers, verify = False, allow_redirects = True, timeout = 30)
			self.__print_debug("Response Status Code", response.status_code)
			if response.status_code == 200:
				html = response.text
			elif response.status_code == 429:
				self.__error = Error.RATE_LIMIT
		except (requests.exceptions.RequestException, urllib3.exceptions.HTTPError) as ex:
			self.__error = Error.REQUEST
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
		return tmp.split("#:~:text=")[0]

	def search(self) -> list[str]:
		"""
		Start a Google search.
		"""
		results = set()
		self.__error = None
		self.__print_debug("Initial Headers", self.__headers)
		self.__print_debug("Initial Cookies", self.__cookies)
		self.__print_debug("Initial Proxy", self.__proxy)
		with requests.Session() as session:
			session.cookies.update(self.__cookies)
			session.proxies = {"https": self.__proxy, "http": self.__proxy} if self.__proxy else {}
			session.max_redirects = 10
			self.__get_page(session, self.__urls.homepage)
			if not self.__error:
				self.__update_consent_cookie(session)
				self.__print_debug("Final Cookies", session.cookies.get_dict())
				while True:
					self.__sleep_random()
					html = self.__get_page(session, self.__get_paginated_search_url())
					# self.__print_debug("HTML", html)
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
		results = list(results)
		# self.__print_debug("Results", results)
		return results
