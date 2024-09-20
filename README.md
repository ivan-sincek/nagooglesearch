# Not Another Google Search

Not another Google searching library. Just kidding, it is.

Tested on Kali Linux v2023.4 (64-bit).

Made for educational purposes. I hope it will help!

## How to Install

```bash
pip3 install nagooglesearch

pip3 install --upgrade nagooglesearch
```

## How to Build and Install Manually

Run the following commands:

```bash
git clone https://github.com/ivan-sincek/nagooglesearch && cd nagooglesearch

python3 -m pip install --upgrade build

python3 -m build

python3 -m pip install dist/nagooglesearch-7.0-py3-none-any.whl
```

## Usage

Default values:

```python
nagooglesearch.SearchClient(
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
)
```

**Only domains without `google` keyword are accepted as valid results. Final output is a unique and sorted list of URLs.**

---

```python
from nagooglesearch import nagooglesearch

# non-string, empty, and duplicate query string parameters will be ignored
# case-sensitive
# search the internet for more query string parameters
parameters = {
	"q": "site:*.example.com intext:password", # search query, required
	"tbs": "li:1", # specify 'li:1' for verbatim search, i.e. do not search alternate spellings, etc.
	"hl": "en",
	"lr": "lang_en",
	"cr": "countryUS",
	"filter": "0", # specify '0' to display hidden results
	"safe": "images", # specify 'images' to turn off safe search, or specify 'active' to turn on safe search
	"num": "80" # number of results per page
}

# this query string parameters will be set only if 'start' query string parameter is not set or is zero
# mimic homepage search as the first request
homepage_parameters = {
	"btnK": "Google+Search",
	"source": "hp"
}

client = nagooglesearch.SearchClient(
	tld = "com", # top level domain, e.g. www.google.com or www.google.hr
	parameters = parameters,
	homepage_parameters = homepage_parameters,
	max_results = 200, # maximum unique urls to return
	user_agent = "curl/3.30.1", # assign random if not set or is empty
	proxy = "socks5://127.0.0.1:9050", # ignore if URL scheme is not 'http[s], 'socks4[h]', or 'socks5[h]'
	min_sleep = 15, # minimum sleep between page requests
	max_sleep = 30, # maximum sleep between page requests
	verbose = False # debug output
)

urls = client.search()

rate_limit = client.get_rate_limit()
if rate_limit in urls:
	urls.pop(urls.index(rate_limit))
	print("[ HTTP 429 Too Many Requests ]")
	# do something

exception = client.get_exception()
if exception in urls:
	urls.pop(urls.index(exception))
	print("[ Requests Exception ]")
	# do something

for url in urls:
	print(url)
	# do something
```

If `max_results` is set to e.g. `200` and `num` is set to e.g. `80`, then, maximum unique urls to return could actually reach `240`.

Check the user agents list [here](https://github.com/ivan-sincek/nagooglesearch/blob/main/src/nagooglesearch/user_agents.txt). For more user agents, check [scrapeops.io](https://scrapeops.io).

Proxy URL scheme must be either `http[s]`, `socks4[h]`, or `socks5[h]`; otherwise, proxy will be ignored.

---

Shortest possible:

```python
from nagooglesearch import nagooglesearch

urls = nagooglesearch.SearchClient(parameters = {"q": "site:*.example.com intext:password"}).search()

# do something
```

---

Time sensitive search (e.g. do not show results older than 6 months):

```python
from nagooglesearch import nagooglesearch
import dateutil.relativedelta as relativedelta

def get_tbs(months):
	today = datetime.datetime.today()
	return nagooglesearch.get_tbs(today, today - relativedelta.relativedelta(months = months))

parameters = {
	"tbs": get_tbs(6)
}

# do something
```

---

Get a random user agent:

```python
from nagooglesearch import nagooglesearch

user_agent = nagooglesearch.get_random_user_agent()
print(user_agent)

# do something
```

Get the user agents list:

```python
from nagooglesearch import nagooglesearch

user_agents = nagooglesearch.get_all_user_agents()
print(user_agents)

# do something
```
