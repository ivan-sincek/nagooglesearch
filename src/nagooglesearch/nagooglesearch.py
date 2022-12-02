#!/usr/bin/env python3

import os
import random
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
import regex as re
import json

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

def get_random_user_agent():
	array = []
	file = os.path.abspath(os.path.split(__file__)[0]) + os.path.sep + "user_agents.txt"
	if os.path.isfile(file) and os.access(file, os.R_OK) and os.stat(file).st_size > 0:
		with open(file, "r", encoding = "ISO-8859-1") as stream:
			for line in stream:
				line = line.strip()
				if line:
					array.append(line)
		stream.close()
	return array[random.randint(0, len(array) - 1)] if array else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.67 Safari/537.36 Edg/87.0.664.52"

def get_tbs(date_from, date_to):
	return ("cdr:1,cd_min:{0},cd_max:{1}").format(date_from.strftime("%m/%d/%Y"), date_to.strftime("%m/%d/%Y"))

class SearchClient:

	def __init__(
		self,
		tld = "com",
		parameters = {},
		homepage_parameters = {
			"btnK": "Google+Search",
			"source": "hp"
		},
		max_results = 100,
		user_agent = "",
		proxy = "",
		min_sleep = 8,
		max_sleep = 18,
		verbose = False
	):
		self.verbose = verbose
		self.max_sleep = max_sleep
		self.min_sleep = min_sleep
		self.max_results = max_results
		self.pagination = {"start": 0, "num": 10}
		self.urls = self.__get_urls(tld, parameters, homepage_parameters)
		self.session = None
		self.proxies = self.__get_proxies(proxy)
		self.headers = self.__get_headers(user_agent)
		self.rate_limit = "429_TOO_MANY_REQUESTS"

	def __jdump(self, data):
		return json.dumps(data, indent = 4, ensure_ascii = False)

	def __debug(self, title, text, json = False):
		if self.verbose:
			print(("{0}: {1}").format(title, self.__jdump(text) if json else text))

	def __unique(self, array):
		seen = set()
		return [x for x in array if not (x in seen or seen.add(x))]

	def __get_proxies(self, proxy):
		proxies = {}
		if proxy:
			proxy = urllib.parse.urlparse(proxy)
			if proxy.scheme.lower() not in ["http", "https", "socks5", "socks5h"]:
				self.__debug("Error", "Proxy URL scheme must be either 'http', 'https', 'socks5', or 'socks5h'. Ignoring the proxy...")
			else:
				proxies["http"] = proxies["https"] = proxy.geturl()
		self.__debug("Proxies", proxies, True)
		return proxies

	def __get_headers(self, user_agent):
		if not user_agent:
			user_agent = get_random_user_agent()
		headers = {
			"Accept": "*/*",
			"Accept-Language": "*",
			"Referer": self.urls["homepage"] + "/",
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": user_agent
		}
		self.__debug("Headers", headers, True)
		return headers

	def __set_pagination(self, key, value):
		try:
			self.pagination[key] = int(value)
		except ValueError:
			self.__debug("Error", ("Cannot convert '{0}' query string parameter to an integer type. Using '{1}' as a default integer value...").format(key, self.pagination[key]))

	def __get_urls(self, tld, parameters, homepage_parameters):
		tmp = {
			"homepage": ("https://www.google.{0}").format(tld.rstrip("/").lower()),
			"search": "",
			"homepage_search": "",
			"const": "?"
		}
		if "q" not in parameters:
			self.__debug("Error", "No 'q' query string parameter was found... Ignoring all the searches...")
		else:
			tmp["search"] = tmp["homepage"] + "/search"
			exists = []
			for key in parameters:
				if isinstance(parameters[key], str) and parameters[key] and key not in exists:
					exists.append(key)
					if key in ["start", "num"]:
						self.__set_pagination(key, parameters[key])
						if key == "start":
							continue
					tmp["search"] += tmp["const"] + ("{0}={1}").format(urllib.parse.quote_plus(key), urllib.parse.quote_plus(parameters[key]))
					tmp["const"] = "&"
			tmp["homepage_search"] = tmp["search"]
			const = tmp["const"]
			for key in homepage_parameters:
				if isinstance(homepage_parameters[key], str) and homepage_parameters[key] and key not in exists:
					exists.append(key)
					tmp["homepage_search"] += const + ("{0}={1}").format(urllib.parse.quote_plus(key), urllib.parse.quote_plus(homepage_parameters[key]))
					const = "&"
		return tmp

	def __get_paginated_search_url(self):
		url = self.urls["homepage_search"]
		if self.pagination["start"] != 0:
			url = self.urls["search"] + self.urls["const"] + ("start={0}").format(self.pagination["start"])
		self.pagination["start"] += self.pagination["num"]
		return url

	def __validate_url(self, url):
		self.__debug("Anchor", url)
		link = None
		url = urllib.parse.urlparse(url)
		if url.netloc and "google" not in url.netloc.lower():
			link = url.geturl()
		else:
			query_string = urllib.parse.parse_qs(url.query)
			for key in query_string:
				if key in ["q", "u", "url"]:
					url = urllib.parse.urlparse(query_string[key][0])
					if url.netloc and "google" not in url.netloc.lower():
						link = url.geturl()
					break
		return link

	def __get_page(self, url):
		self.__debug("Requesting", url)
		html = ""
		response = None
		try:
			response = self.session.get(url, headers = self.headers, proxies = self.proxies, timeout = 30, verify = False, allow_redirects = True)
			self.__debug("Status", response.status_code)
			cookies = self.session.cookies.get_dict()
			key = "CONSENT"
			if key in cookies and re.search(r"PENDING\+[\d]+", cookies[key], re.IGNORECASE):
				self.__debug("Info", ("Looks like your IP address is sourcing from the EU location. Your search results may vary. Trying to work around this by updating the '{0}' cookie...").format(key))
				cookies[key] = ("YES+shp.gws-20211108-0-RC1.fr+F+{0}").format(cookies[key].split("+")[1])
				self.session.cookies.clear()
				self.session.cookies.update(cookies)
			self.__debug("Cookies", self.session.cookies.get_dict(), True)
			if response.status_code == 200:
				html = response.text
			elif response.status_code == 429:
				html = self.rate_limit
		except requests.exceptions.RequestException as ex:
			self.__debug("Exception", ex)
		finally:
			if response is not None:
				response.close()
		return html

	def search(self):
		results = []
		if self.urls["search"]:
			self.session = requests.Session()
			self.session.max_redirects = 10
			self.__get_page(self.urls["homepage"])
			while True:
				time.sleep(random.randint(self.min_sleep, self.max_sleep))
				html = self.__get_page(self.__get_paginated_search_url())
				if html == self.rate_limit:
					results.append(self.rate_limit)
					break
				soup = BeautifulSoup(html, "html.parser")
				anchors = None
				try:
					anchors = soup.find(id = "search").find_all("a")
				except AttributeError:
					gbar = soup.find(id = "gbar")
					if gbar:
						gbar.clear()
					anchors = soup.find_all("a")
				found = False
				for anchor in anchors:
					try:
						anchor = self.__validate_url(anchor["href"])
						if anchor:
							results.append(anchor)
							found = True
					except KeyError:
						pass
				results = self.__unique(results)
				if not found or len(results) >= self.max_results:
					break
			self.session.close()
			results = sorted(results, key = str.casefold)
		self.__debug("Results", results, True)
		return results
