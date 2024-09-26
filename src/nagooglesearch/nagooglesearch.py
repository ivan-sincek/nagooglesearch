#!/usr/bin/env python3

import json, os, random, re, requests, time, urllib.parse

from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

default_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def get_all_user_agents():
	array = []
	file = os.path.join(os.path.abspath(os.path.split(__file__)[0]), "user_agents.txt")
	if os.path.isfile(file) and os.access(file, os.R_OK) and os.stat(file).st_size > 0:
		with open(file, "r", encoding = "UTF-8") as stream:
			for line in stream:
				line = line.strip()
				if line:
					array.append(line)
	return array if array else [default_agent]

def get_random_user_agent():
	array = get_all_user_agents()
	return array[random.randint(0, len(array) - 1)]

def get_tbs(date_from, date_to):
	date_format = "%m/%d/%Y"
	return ("cdr:1,cd_min:{0},cd_max:{1}").format(date_from.strftime(date_format), date_to.strftime(date_format))

class SearchClient:

	__error = ""
	__init_error = "INIT_ERROR"
	__requests_error = "REQUESTS_EXCEPTION"
	__rate_limit_error = "429_TOO_MANY_REQUESTS"

	def __init__(
		self,
		tld = "com",
		homepage_parameters = {
			"btnK": "Google+Search",
			"source": "hp"
		},
		search_parameters = {},
		user_agent = "",
		proxy = "",
		max_results = 100,
		min_sleep = 8,
		max_sleep = 18,
		debug = False
	):
		self.__debug = debug
		self.__tld = tld
		self.__homepage_parameters = self.__get_homepage_parameters(homepage_parameters)
		self.__search_parameters = self.__get_search_parameters(search_parameters)
		self.__pagination = self.__get_pagination()
		self.__urls = self.__get_urls()
		self.__headers = self.__get_headers(user_agent)
		self.__cookies = self.__get_cookies()
		self.__proxies = self.__get_proxies(proxy)
		self.__max_results = self.__get_max_results(max_results)
		self.__min_sleep = self.__get_min_sleep(min_sleep)
		self.__max_sleep = self.__get_max_sleep(max_sleep)

	def get_error(self):
		return self.__error

	def __jdump(self, data):
		return json.dumps(data, indent = 4, ensure_ascii = False)

	def __print(self, title, text, json = False):
		if self.__debug:
			print(("{0}: {1}").format(title, self.__jdump(text) if json else text))

	def __get_homepage_parameters(self, homepage_parameters):
		if not isinstance(homepage_parameters, dict):
			self.__error = self.__init_error
			self.__print("Error", "The 'homepage_parameters' parameter must be a dictionary.")
		return homepage_parameters

	def __get_search_parameters(self, search_parameters):
		if not isinstance(search_parameters, dict):
			self.__error = self.__init_error
			self.__print("Error", "The 'search_parameters' parameter must be a dictionary.")
		return search_parameters

	def __get_pagination(self):
		pagination = {"start": 0, "num": 10}
		if not self.__error:
			for key in pagination.keys():
				if key in self.__search_parameters:
					try:
						pagination[key] = int(self.__search_parameters[key])
						if pagination[key] < 0:
							self.__error = self.__init_error
							self.__print("Error", ("The '{0}' query string parameter must be greater than or equal to zero.").format(key))
					except (TypeError, ValueError):
						self.__error = self.__init_error
						self.__print("Error", ("Cannot convert the '{0}' query string parameter to the integer type.").format(key))
		return pagination

	def __get_urls(self):
		tmp = {"homepage": "", "search_from_homepage": "", "search": ""}
		if not self.__error:
			self.__search_parameters.pop("start", None)
			self.__homepage_parameters.update(self.__search_parameters)
			tmp["homepage"] = self.__get_url()
			tmp["search_from_homepage"] = self.__get_url("/search", self.__homepage_parameters)
			tmp["search"] = self.__get_url("/search", self.__search_parameters)
		return tmp

	def __get_url(self, path = "/", search_parameters = {}):
		return urllib.parse.urlunsplit(("https", ("www.google.{0}").format(str(self.__tld).lower()), path, urllib.parse.urlencode(search_parameters, doseq = True) if search_parameters else "", ""))

	def __get_headers(self, user_agent):
		if not user_agent:
			user_agent = get_random_user_agent()
		return {
			"Accept": "*/*",
			"Accept-Language": "*",
			"Referer": self.__urls["homepage"],
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": str(user_agent)
		}

	def __get_cookies(self):
		return {
			"SOCS": "CAESHAgCEhJnd3NfMjAyNDA5MjMtMF9SQzEaAmRlIAEaBgiApc23Bg" # NOTE: New cookie consent method. This cookie is valid for 13 months, created on 2024-09-23.
		}

	def __get_proxies(self, proxy):
		proxies = {}
		if proxy:
			proxy = urllib.parse.urlsplit(proxy)
			if proxy.scheme.lower() not in ["http", "https", "socks4", "socks4h", "socks5", "socks5h"]:
				self.__error = self.__init_error
				self.__print("Error", "Proxy URL scheme must be either 'http[s]', 'socks4[h]', or 'socks5[h]'.")
			else:
				proxies["http"] = proxies["https"] = proxy.geturl()
		return proxies

	def __get_max_results(self, max_results):
		try:
			max_results = int(max_results)
			if max_results < 0:
				self.__error = self.__init_error
				self.__print("Error", "The 'max_results' parameter must be greater than or equal to zero.")
		except (TypeError, ValueError):
			self.__error = self.__init_error
			self.__print("Error", "Cannot convert the 'max_results' parameter to the integer type.")
		return max_results

	def __get_min_sleep(self, min_sleep):
		try:
			min_sleep = int(min_sleep)
			if min_sleep < 0:
				self.__error = self.__init_error
				self.__print("Error", "The 'min_sleep' must be greater than or equal to zero.")
		except (TypeError, ValueError):
			self.__error = self.__init_error
			self.__print("Error", "Cannot convert the 'min_sleep' parameter to the integer type.")
		return min_sleep

	def __get_max_sleep(self, max_sleep):
		try:
			max_sleep = int(max_sleep)
			if max_sleep < self.__min_sleep:
				self.__error = self.__init_error
				self.__print("Error", "The 'max_sleep' parameter must be greater than or equal to 'min_sleep' parameter.")
		except (TypeError, ValueError):
			self.__error = self.__init_error
			self.__print("Error", "Cannot convert the 'max_sleep' parameter to the integer type.")
		return max_sleep

	def __get_page(self, session, url):
		self.__print("Request", url)
		html = ""
		response = None
		try:
			response = session.get(url, headers = self.__headers, verify = False, allow_redirects = True, timeout = 30)
			self.__print("Status Code", response.status_code)
			if response.status_code == 200:
				html = response.text
			elif response.status_code == 429:
				self.__error = self.__rate_limit_error
		except (requests.packages.urllib3.exceptions.LocationParseError, requests.exceptions.RequestException) as ex:
			self.__error = self.__requests_error
			self.__print("Exception", ex)
		finally:
			if response:
				response.close()
		return html

	def __get_paginated_search_url(self):
		url = self.__urls["search"] + ("&start={0}").format(self.__pagination["start"]) if self.__pagination["start"] > 0 else self.__urls["search_from_homepage"]
		self.__pagination["start"] += self.__pagination["num"]
		return url

	def __validate_url(self, url):
		# self.__print("Anchor", url)
		link = ""
		url = urllib.parse.urlsplit(url)
		domain = url.netloc.lower()
		if domain and "google" not in domain and not domain.endswith("goo.gl"):
			link = url.geturl()
		else:
			query_string = urllib.parse.parse_qs(url.query)
			for key in query_string:
				if key in ["q", "u", "url"]:
					url = urllib.parse.urlsplit(query_string[key][0])
					domain = url.netloc.lower()
					if domain and "google" not in domain and not domain.endswith("goo.gl"):
						link = url.geturl()
						break
		return link

	def search(self):
		results = set()
		if self.__error != self.__init_error:
			self.__error = ""
			self.__print("Headers", self.__headers, True)
			self.__print("Cookies", self.__cookies, True)
			self.__print("Proxies", self.__proxies, True)
			session = requests.Session()
			session.max_redirects = 10
			session.cookies.update(self.__cookies)
			session.proxies = self.__proxies
			self.__get_page(session, self.__urls["homepage"])
			if not self.__error:
				cookies = session.cookies.get_dict()
				key = "CONSENT"
				if key in cookies and re.search(r"PENDING\+[\d]+", cookies[key], re.IGNORECASE):
					# NOTE: Old cookie consent method.
					self.__print("Info", ("Looks like your IP address is originating from an EU location. Your search results may vary. Attempting to work around this by updating the '{0}' cookie...").format(key))
					cookies[key] = ("YES+shp.gws-20240923-0-RC1.fr+F+{0}").format(cookies[key].split("+", 1)[-1])
					session.cookies.clear()
					session.cookies.update(cookies)
					self.__print("Updated Cookies", session.cookies.get_dict(), True)
				while True:
					time.sleep(random.randint(self.__min_sleep, self.__max_sleep))
					html = self.__get_page(session, self.__get_paginated_search_url())
					if self.__error:
						break
					soup = BeautifulSoup(html, "html.parser")
					anchors = soup.find(id = "search")
					if anchors:
						anchors = anchors.find_all("a", href = True)
					else:
						for identifier in ["gbar", "top_nav", "searchform"]:
							identifier = soup.find(id = identifier)
							if identifier:
								identifier.clear()
						anchors = soup.find_all("a", href = True)
					found = False
					for anchor in anchors:
						anchor = self.__validate_url(anchor["href"])
						if anchor:
							found = True
							results.add(anchor)
					if not found or len(results) >= self.__max_results:
						break
				results = sorted(results, key = str.casefold)
			session.close()
		results = list(results)
		# self.__print("Results", results, True)
		return results
