import os
import zipfile
from bangs.bangs import BangsManager
from bangs.bangs import DBang
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import PreferencesEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
import os.path
import html
from enum import Enum

storage_path = os.path.join(os.path.dirname(__file__), ".bangs-cache")
extension_icon = "icons/ddg_icon.png"
error_icon = "icons/bang.svg"
unknown_icon = "icons/unknown.svg"
favicons_path = "icons/pages_colors"
icons_zip = "icons.zip"


class ExtensionState(Enum):
    STARTING = "Extension is starting..."
    DBANG_LOADING_FAILED = "Could not load successfully. Please restart ulauncher. and check logs"
    READY = "ok"

    def __str__(self):
        return self.value


class DBangsExtension(Extension):
    def __init__(self):
        super(DBangsExtension, self).__init__()
        self.status = ExtensionState.STARTING
        self.subscribe(KeywordQueryEvent, DBangsKeywordQueryListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(ItemEnterEvent, OpenNewestUrlActionListener())

    def load_bangs_and_icons(self, force_download):
        try:
            self.bangs = BangsManager(storage_path).get_latest(
                force_download=force_download)
            self.icons = DomainIconsManager(
                icons_zip, favicons_path, self.bangs, unknown_icon)
            self.status = ExtensionState.READY
        except Exception as e:
            print("Error while loaded the DuckDuckGo Bangs and Icons", e)
            self.status = ExtensionState.DBANG_LOADING_FAILED


class PreferencesEventListener(EventListener):
    """
    Finishes initialization once ulauncher has loaded the preferences
    """

    def on_event(self, event: PreferencesEvent, extension: DBangsExtension):
        force_download = True
        if event.preferences["force_download"].lower() == "never":
            force_download = False
        extension.load_bangs_and_icons(force_download)


class DBangsKeywordQueryListener(EventListener):

    def on_event(self, event, extension):
        # check if extension is ready, otherwise print the current status and abort
        if extension.status is not ExtensionState.READY:
            return make_status_result(extension)

        argument = event.get_argument()
        extension.newest_query = argument
        if argument is None or argument == "":
            return self.do_nothing_result("Enter a term to search for DuckDuckGo Bangs")

        search_terms = argument.split(" ")
        items = self.make_bangs_results(extension, search_terms)

        return RenderResultListAction(items)

    def make_status_result(self, extension):
        icon = extension_icon
        if extension.status is ExtensionState.DBANG_LOADING_FAILED:
            icon = error_icon
        text = str(extension.status)
        return self.do_nothing_result(text, icon)

    def do_nothing_result(self, text, icon=extension_icon):
        return RenderResultListAction([
            ExtensionResultItem(icon=extension_icon,
                                name=text,
                                on_enter=DoNothingAction())
        ])

    def make_bangs_results(self, extension, search_terms: list):
        """
        Searches for DBangs using the search terms and checks if the first search terms already matches a known DBang.
        Creates the ResultItems and returns them.
        """
        items = []
        used_urls = []  # contains a list of shown urls, for making sure that no url is shown twice

        # check if the first string already matches a term of any dbang.
        matches_exactly: DBang = extension.bangs.match_exactly(search_terms[0])
        if matches_exactly is not None:
            item = self._generate_result_item_from_exact_match(
                extension, dbang=matches_exactly, search_terms=search_terms)
            items.append(item)
            used_urls.append(matches_exactly.url)

        # search in all DBangs for the typed terms
        max_results = int(extension.preferences["max_results"])
        results = extension.bangs.search(contains=search_terms)
        counter = 0
        for entry in results:
            # make sure that no url is shown twice
            if entry.url in used_urls:
                continue

            # generate the query that will be set if the user chooses this action
            new_query = self._make_query(extension, entry)
            title = "{0} | {1} | {2}".format(self.escape_html(entry.t), self.make_site_title(entry), self.make_bang_description(
                entry))
            items.append(ExtensionSmallResultItem(name=title,
                                                  icon=extension.icons.get_icon_path(
                                                      entry),
                                                  on_enter=SetUserQueryAction(new_query)))
            used_urls.append(entry.url)
            counter += 1
            if counter >= max_results:
                break
        return items

    def _generate_result_item_from_exact_match(self, extension, dbang: DBang, search_terms: list):
        """
        Generates the result item for an exact dbang match
        case 1) the query is already in the correct format: If the user clicks on the item, the url should be opened
            example: "! w Ulauncher" -> opens a Wikipedia search for Ulauncher in the browser
        case 2) otherwise the query is set to the right format, with the Dbang term in front
            example: ! wikipedia search" -> sets the query to "! w ", and in the next query event case 1 will apply
        """
        if len(search_terms) > 1:
            search_text = " ".join(search_terms[1:])
            title = "{0} | {1}: Search for \"{2}\"".format(
                dbang.t, self.make_site_title(dbang), self.escape_html(search_text))
            # The url is not generated right away, as the search term still change
            # The ExtensionCustomAction below will be received by OpenNewestUrlActionListener,
            # which takes the newest query that the user has typed for url generation
            action = ExtensionCustomAction(dbang, keep_app_open=True)

        else:
            title = "{0} | {1}: Enter search term".format(
                dbang.t, self.make_site_title(dbang))
            new_query = self._make_query(extension, dbang)
            action = SetUserQueryAction(new_query)

        return ExtensionResultItem(name=title,
                                   icon=extension.icons.get_icon_path(
                                       dbang),
                                   description=self.make_bang_description(
                                       dbang),
                                   on_enter=action)

    def make_site_title(self, dbang):
        """ Returns the capitalized and html-escaped title for the dbang entry"""
        return self.escape_html(dbang.site.capitalize())

    def _make_query(self, extension, bangs_entry):
        """Generates and returns the ulauncher user query for a given DBang entry"""
        return extension.preferences["keyword"] + " " + bangs_entry.t + " "

    def make_bang_description(self, entry):
        """Returns the description for a given DBang"""
        return "{1} > {2} > {0}".format(
            entry.domain, entry.category, entry.subcategory)

    def escape_html(self, text):
        escaped = html.escape(text.replace("&", " (and) "))
        return escaped


class OpenNewestUrlActionListener(EventListener):
    """
    Custom Action that creates the url for a selected dbang from the newest entered query.
    Due to high latency, the newest query can be different from the one that was present when the ResultItem was generated
    Example: 
        1. user types "! wa 2+x=4"
        2. for each character that the user types, a search is performed and an own result list generated
        3. The user presses enter instantly after he finishes typing
        4. The first result item is still showing "! wa 2+x=" (without the last character "4" at the end)
    This is why the newest query that the user has typed is used here
    """

    def on_event(self, event, extension):
        dbang: DBang = event.get_data()
        newest_search_text = extension.newest_query[len(dbang.t)+1:]
        url = dbang.get_url(newest_search_text)
        return OpenUrlAction(url)


def relative_file_exists(file):
    return os.path.exists(os.path.join(os.path.dirname(__file__), file))


class DomainIconsManager():
    """
    Manages the website icons that are shown in each ResultItem.
    The icons are bundled in a zip file and are unpacked to a folder once. 
    """

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
        """
        The favicons are bundled in a zip file and must be unpacked once. 
        This method checks if that was already done before.
        """
        if not os.path.exists(full_expected_path):
            os.mkdir(full_expected_path)
            with zipfile.ZipFile(full_zip_file, 'r') as zip_ref:
                zip_ref.extractall(full_expected_path)


if __name__ == '__main__':
    DBangsExtension().run()
