"""Persist editable defaults and custom shortcuts without resurrecting removals."""
import uuid
from urllib.parse import unquote, urlsplit

from .model import BVKS_PATH, CHANNELS, TREE_HOME, TREE_HOST, UserError, tree_media_url, tree_path, tree_url, youtube_url


def normalize_link(value, mode='videos'):
    value = value.strip()
    if urlsplit(value).hostname == TREE_HOST:
        path = tree_path(value)
        return 'tree', tree_media_url(path) if path.lower().endswith('.mp3') else tree_url(path), 'videos'
    tail = unquote(urlsplit(value).path).rstrip('/').rsplit('/', 1)[-1]
    mode = tail if tail in ('videos', 'playlists') else mode
    url, _ = youtube_url(value, mode)
    return 'youtube', url, mode


def defaults():
    items = [('tree-home', 'All Desire Tree audio', TREE_HOME),
             ('prabhupada', 'Śrīla Prabhupāda', tree_url('/01_-_Srila_Prabhupada')),
             ('bvks', 'Bhakti Vikasa Swami', tree_url(BVKS_PATH))]
    items += [(f'channel-{i}', title, url) for i, (title, url) in enumerate(CHANNELS)]
    result = []
    for key, title, link in items:
        source, url, mode = normalize_link(link)
        result.append(dict(id='default:' + key, name=title, source=source, url=url, mode=mode))
    return result


class Shortcuts:
    def __init__(self, state):
        self.state = state
        self.items = state.get('shortcuts')
        if self.items is None:
            self.items = defaults()
            self.save()

    def save(self):
        self.state.put('shortcuts', self.items)

    def put(self, name, link, item_id=None, mode='videos'):
        if not name.strip():
            raise UserError('Enter a name for this shortcut.')
        source, url, mode = normalize_link(link, mode)
        if any(item['url'] == url and item['id'] != item_id for item in self.items):
            raise UserError('This link is already in your shortcuts. Edit the existing shortcut instead.')
        item = dict(id=item_id or 'custom:' + uuid.uuid4().hex, name=name.strip(), source=source, url=url, mode=mode)
        index = next((i for i, old in enumerate(self.items) if old['id'] == item_id), len(self.items))
        if index == len(self.items):
            self.items.append(item)
        else:
            self.items[index] = item
        self.save()
        return item

    def remove(self, item_id):
        self.items = [item for item in self.items if item['id'] != item_id]
        self.save()

    def restore(self):
        custom = [i for i in self.items if not i['id'].startswith('default:')]
        urls = {i['url'] for i in custom}
        self.items = [i for i in defaults() if i['url'] not in urls] + custom
        self.save()
