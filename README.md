# Not Another Google Search

Not another Google searching library. Just kidding - it is.

Made for educational purposes. I hope it will help!

Future plans:

* ability to set/rotate search parameters, user agents, and proxies without reinitialization.

## Table of Contents

* [How to Install](#how-to-install)
	* [Standard Install](#standard-install)
	* [Build and Install From the Source](#build-and-install-from-the-source)
* [Usage](#usage)
	* [Standard](#standard)
	* [Shortest Possible](#shortest-possible)
	* [Time Sensitive Search](#time-sensitive-search)
	* [User Agents](#user-agents)

## How to Install

### Standard Install

```bash
pip3 install nagooglesearch

pip3 install --upgrade nagooglesearch
```

### Build and Install From the Source

Run the following commands:

```bash
git clone https://github.com/ivan-sincek/nagooglesearch && cd nagooglesearch

python3 -m pip install --upgrade build

python3 -m build

python3 -m pip install dist/nagooglesearch-8.0-py3-none-any.whl
```

## Usage

### Standard

Default values:

```python
nagooglesearch.GoogleClient(
	tld = "com",
	homepage_parameters = {
		"btnK": "Google+Search",
		"source": "hp"
	},
	search_parameters = {
	},
	user_agent = "",
	proxy = "",
	max_results = 100,
	min_sleep = 8,
	max_sleep = 18,
	debug = False
)
```

**Only domains without they keyword `google` and not ending with the keyword `goo.gl` are accepted as valid results. The final output is a unique and sorted list of URLs.**

Example, standard:

```python
import nagooglesearch

# the following query string parameters are set only if 'start' query string parameter is not set or is equal to zero
# simulate a homepage search
homepage_parameters = {
	"btnK": "Google+Search",
	"source": "hp"
}

# search the internet for additional query string parameters
search_parameters = {
	"q": "site:*.example.com intext:password", # search query
	"tbs": "li:1", # specify 'li:1' for verbatim search (no alternate spellings, etc.)
	"hl": "en",
	"lr": "lang_en",
	"cr": "countryUS",
	"filter": "0", # specify '0' to display hidden results
	"safe": "images", # specify 'images' to turn off safe search, or specify 'active' to turn on safe search
	"num": "80" # number of results per page
}

client = nagooglesearch.GoogleClient(
	tld = "com", # top level domain, e.g., www.google.com or www.google.hr
	homepage_parameters = homepage_parameters, # 'search_parameters' will override 'homepage_parameters'
	search_parameters = search_parameters,
	user_agent = "curl/3.30.1", # a random user agent will be set if none is provided
	proxy = "socks5://127.0.0.1:9050", # one of the supported URL schemes are 'http[s]', 'socks4[h]', and 'socks5[h]'
	max_results = 200, # maximum unique URLs to return
	min_sleep = 15, # minimum sleep between page requests
	max_sleep = 30, # maximum sleep between page requests
	debug = True # enable debug output
)

urls = client.search()

if client.get_error() == "REQUESTS_EXCEPTION":
	print("[ Requests Exception ]")
	# do something
elif client.get_error() == "429_TOO_MANY_REQUESTS":
	print("[ HTTP 429 Too Many Requests ]")
	# do something

for url in urls:
	print(url)
	# do something
```

If `max_results` is set to, e.g., `200` and `num` is set to, e.g., `80`, then, maximum unique URLs that could be returned could actually reach `240`.

Check the list of user agents [here](https://github.com/ivan-sincek/bot-safe-agents/blob/main/src/bot_safe_agents/user_agents.txt). For more user agents, check [scrapeops.io](https://scrapeops.io).

### Shortest Possible

Example, shortest possible:

```python
import nagooglesearch

urls = nagooglesearch.GoogleClient(search_parameters = {"q": "site:*.example.com intext:password"}).search()

# do something
```

### Time Sensitive Search

Example, do not show results older than 6 months:

```python
import nagooglesearch, dateutil.relativedelta as relativedelta

def get_tbs(months):
	today = datetime.datetime.today()
	return nagooglesearch.get_tbs(today, today - relativedelta.relativedelta(months = months))

search_parameters = {
	"tbs": get_tbs(6)
}

# do something
```

### User Agents

Example, get all user agents:

```python
import nagooglesearch

user_agents = nagooglesearch.get_all_user_agents()
print(user_agents)

# do something
```

Example, get a random user agent:

```python
import nagooglesearch

user_agent = nagooglesearch.get_random_user_agent()
print(user_agent)

# do something
```
