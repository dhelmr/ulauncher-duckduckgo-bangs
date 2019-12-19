import os
import logging
import zipfile
from bangs.bangs import BangsManager
from bangs.bangs import DBang
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
import os.path
import html
import re

storage_path = os.path.join(os.path.dirname(__file__), ".bangs-cache")
extension_icon = "icons/bang.svg"
bang_selected_icon = "icons/arrow-right.svg"
unknown_icon = "icons/unknown.svg"
favicons_path = "icons/pages_colors"
icons_zip = "icons.zip"
bangs = BangsManager(storage_path).get_latest()


class DBangsExtension(Extension):
    def __init__(self):
        super(DBangsExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.icons = DomainIconsManager(
            icons_zip, favicons_path, bangs, unknown_icon)


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        argument = event.get_argument()
        if argument is None or argument == "":
            return RenderResultListAction([
                ExtensionResultItem(icon=extension_icon,
                                    name='Search for DuckDuckGo bangs...',
                                    on_enter=DoNothingAction())
            ])
        search_terms = argument.split(" ")
        items = []
        used_urls = []  # contains a list of shown urls, for making sure that no url is shown twice

        # check if the first string already matches a term of any dbang.
        matches_exactly: DBang = bangs.match_exactly(search_terms[0])
        if matches_exactly is not None:
            item = self._generate_result_item_from_exact_match(
                extension, dbang=matches_exactly, search_terms=search_terms)
            items.append(item)
            used_urls.append(matches_exactly.url)

        # search in all DBangs for the typed terms
        max_results = int(extension.preferences["max_results"])
        results = bangs.search(contains=search_terms)
        counter = 0
        for entry in results:
            # make sure that no url is shown twice
            if entry.url in used_urls:
                continue

            # generate the query that will be set if the user chooses this action
            new_query = self._make_query(extension, entry)
            title = "{0} | {1} | {2}".format(entry.t, self.make_site_title(entry), self.make_bang_description(
                entry))
            items.append(ExtensionSmallResultItem(name=title,
                                                  icon=extension.icons.get_icon_path(
                                                      entry),
                                                  on_enter=SetUserQueryAction(new_query)))
            used_urls.append(entry.url)
            counter += 1
            if counter > max_results:
                break

        return RenderResultListAction(items)

    def _generate_result_item_from_exact_match(self, extension, dbang: DBang, search_terms: list):
        if len(search_terms) > 1:
            search_text = " ".join(search_terms[1:])
            url = dbang.get_url(search_text)
            title = "{0} | {1}: Search for {2}".format(
                dbang.t, self.make_site_title(dbang), search_text)
            return ExtensionResultItem(name=title,
                                       description=self.make_bang_description(
                                           dbang),
                                       icon=extension.icons.get_icon_path(
                                           dbang),
                                       on_enter=OpenUrlAction(url))
        else:
            title = "{0} | {1}: Enter search term".format(
                dbang.t, self.make_site_title(dbang))
            new_query = self._make_query(extension, dbang)
            return ExtensionResultItem(name=title,
                                       icon=extension.icons.get_icon_path(
                                           dbang),
                                       description=self.make_bang_description(
                                           dbang),
                                       on_enter=SetUserQueryAction(new_query))

    def make_site_title(self, dbang):
        """ Returns the capitalized title for the dbang entry"""
        if re.match(r".*<.*>.*", dbang.site) is not None:
            # Dirty fix for escaping this sequenceste
            # if there is an empty html tag "< ... >" in the title, ulauncher will fail to display it
            return html.escape(dbang.site.capitalize())
        return dbang.site.capitalize()

    def _make_query(self, extension, bangs_entry):
        """Generates and returns the ulauncher user query for a given DBang entry"""
        return extension.preferences["keyword"] + " " + bangs_entry.t + " "

    def make_bang_description(self, entry):
        """Returns the description for a given DBang"""
        return "{1} > {2} > {0}".format(
            entry.domain, entry.category, entry.subcategory)


def relative_file_exists(file):
    return os.path.exists(os.path.join(os.path.dirname(__file__), file))


class DomainIconsManager():
    def __init__(self, zip_file, folder, dbangs, unknown_icon):
        self.folder = folder
        self.unknown_icon = unknown_icon
        full_favicons_path = os.path.join(os.path.dirname(__file__), folder)
        full_zip_file = os.path.join(os.path.dirname(__file__), zip_file)
        self.check_favicons(full_zip_file, full_favicons_path)
        self.create_cache(dbangs)

    def create_cache(self, dbangs):
        icons_by_site = dict()
        for dbang in dbangs:
            icon_path = os.path.join(self.folder, dbang.domain+".svg")
            if relative_file_exists(icon_path):
                icons_by_site[dbang.domain] = icon_path
        self.icons_by_site = icons_by_site

    def get_icon_path(self, dbang):
        return self.icons_by_site.get(dbang.domain, self.unknown_icon)

    def check_favicons(self, full_zip_file, full_expected_path):
        """The favicons are bundled in a zip file and must be unpacked once"""
        if not os.path.exists(full_expected_path):
            os.mkdir(full_expected_path)
            with zipfile.ZipFile(full_zip_file, 'r') as zip_ref:
                zip_ref.extractall(full_expected_path)


if __name__ == '__main__':
    DBangsExtension().run()
