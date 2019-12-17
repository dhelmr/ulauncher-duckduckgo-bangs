import os
import logging
from bangs.bangs import BangsManager
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

# icons: https://github.com/apancik/public-domain-icons/blob/master/dist/symbol%20arrow%20right%20arrow%20arrow%20right%20direction.svg

logger = logging.getLogger(__name__)
storage_path = os.path.join(os.path.dirname(__file__), ".bangs-cache")
bangs = BangsManager(storage_path).get_latest()
extension_icon = "icons/bang.svg"
bang_selected_icon = "icons/arrow-right.svg"


class EmojiExtension(Extension):

    def __init__(self):
        super(EmojiExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.allowed_skin_tones = ["", "dark", "light",
                                   "medium", "medium-dark", "medium-light"]


class KeywordQueryEventListener(EventListener):

    def make_bang_description(self, entry):
        return "{1} > {2} > {0}".format(
            entry.domain, entry.category, entry.subcategory)

    def on_event(self, event, extension):
        argument = event.get_argument()
        if argument is None or argument == "":
            return RenderResultListAction([
                ExtensionResultItem(icon=extension_icon,
                                    name='Type in duckduckgo bang.',
                                    on_enter=DoNothingAction())
            ])
        search_terms = argument.split(" ")
        matches_exactly = bangs.match_exactly(search_terms[0])
        items = []
        used_urls = []
        if matches_exactly is not None:
            if len(search_terms) > 1:
                search_text = " ".join(search_terms[1:])
                url = matches_exactly.get_url(search_text)
                title = "{0}: Search for {1}".format(
                    matches_exactly.site.capitalize(), search_text)
                items.append(ExtensionResultItem(name=title,
                                                 description=self.make_bang_description(
                                                     matches_exactly),
                                                 icon=bang_selected_icon,
                                                 on_enter=OpenUrlAction(url)))
            else:
                title = matches_exactly.site.capitalize() + ": Enter search term"
                new_query = self._make_query(extension, matches_exactly)
                items.append(ExtensionResultItem(name=title,
                                                 icon=bang_selected_icon,
                                                 description=self.make_bang_description(
                                                     matches_exactly),
                                                 on_enter=SetUserQueryAction(new_query)))
            used_urls.append(matches_exactly.url)

        results = bangs.search(contains=search_terms)

        counter = 0
        for entry in results:
            # make sure that no url is shown twice
            if entry.url in used_urls:
                continue

            # generate the query that will be set if the user chooses this action
            new_query = self._make_query(extension, entry)
            title = "{0} | {1} | {2}".format(entry.t, entry.site.capitalize(), self.make_bang_description(
                entry))
            items.append(ExtensionSmallResultItem(name=title,
            icon=bang_selected_icon,
                                                  on_enter=SetUserQueryAction(new_query)))
            used_urls.append(entry.url)
            counter += 1
            if counter > 7:
                break

        return RenderResultListAction(items)
    
    def _make_query(self,extension, bangs_entry):
        return extension.preferences["keyword"] + " " + bangs_entry.t + " "


if __name__ == '__main__':
    EmojiExtension().run()
