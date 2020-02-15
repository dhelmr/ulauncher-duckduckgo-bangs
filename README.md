# DuckDuckGo Bangs for Ulauncher

This is a extension for [Ulauncher](https://github.com/Ulauncher/Ulauncher) that allows you to browse and use [DuckDuckGo bangs](https://duckduckgo.com/bang). That way it is possible to directly access thousands of site searches from within Ulauncher.

![bang for archlinux](docs/bang_archlinux.png)

# Installation

Go to the extensions tab of Ulauncher's settings, click on 'Add Extension', and enter the name of this repository: `https://github.com/dhelmr/ulauncher-duckduckgo-bangs`.

By default, the extension can be started with the keyword `!`, followed by a space and either a DuckDuckGo Bang, or a search term that will be used for browsing the available websites.

Have a look at [the Ulauncher page](https://ext.ulauncher.io/) for more information about extensions and how to install them.

# Requirements

You need Python 3.7 and Ulauncher >= 5 (Extension API 2.0).

# How does it work?

The information for the bangs can be downloaded from [DuckDuckGo as a JSON file](https://duckduckgo.com/bang.js), and this is what the extension does in the background. It then uses this information (the bang keywords, names, categories and urls) to show you the list in Ulauncher. 

By the extension no requests to DuckDuckGo are made: When you type `! w Linux`, the Web Browser will directly go to `https://en.wikipedia.org/wiki/Special:Search?search=Linux` and not first open a DuckDuckGo search with `!w Linux`. In this manner using the bangs from this extension is potentially faster than from DuckDuckGo.

# Known issues

* Combining `&` and html special characters (like `<` or `>`) will result in an empty result item. [See here](https://github.com/Ulauncher/Ulauncher/issues/477) for more information. The item can selected however and the underlying action, e.g. opening the url, will work too.

# License 

[Licensed under GPLv3](LICENSE.txt). The duckduckgo icon is separately licensed under [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/), by [DuckDuckGo](https://duckduckgo.com/).
