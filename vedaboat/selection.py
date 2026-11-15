from __future__ import annotations

from .model import Entry


class Selection:
    """Selections are independent of both the visible page and search filter."""

    def __init__(self):
        self.entries: dict[str, Entry] = {}
        self.members: dict[str, set[str]] = {}
        self.loading: set[str] = set()
        self.excluded: set[str] = set()
        self.excluded_groups: set[str] = set()
        self.intents: set[str] = set()
        self.parents: dict[str, set[str]] = {}
        self.generation = 0

    def clear(self):
        self.generation += 1
        self.entries.clear()
        self.members.clear()
        self.loading.clear()
        self.excluded.clear()
        self.excluded_groups.clear()
        self.intents.clear()
        self.parents.clear()

    def children(self, entry: Entry) -> set[str]:
        related={key for key in self.entries if entry.key in self.parents.get(key,set())}
        if entry.source == "tree":
            prefix = "tree:" + entry.path.rstrip("/") + "/"
            if entry.path=='/06_-_More':
                related |= {k for k in self.entries if k.startswith(('tree:/04_-_ISKCON_Matajis/','tree:/05_-_ISKCON_Chowpatty/'))}
            return {k for k in self.entries if k.startswith(prefix)} | self.members.get(entry.key, set()) | related
        return self.members.get(entry.key, set()) | related

    def state(self, entry: Entry) -> str:
        if not entry.container:
            return "checked" if entry.key in self.entries else "unchecked"
        members = self.children(entry)
        count = len(members & self.entries.keys())
        if entry.key in self.loading:
            return "loading"
        if count == len(members) and entry.key in self.members and (members or entry.key in self.intents):
            return "checked"
        return "partial" if count else "unchecked"

    def deselect(self, entry: Entry):
        if entry.container:
            self.intents.discard(entry.key)
            self.intents={k for k in self.intents if entry.key not in self.parents.get(k,set()) and not (entry.source=='tree' and k.startswith(entry.key.rstrip('/')+'/'))}
            self.excluded_groups.add(entry.key)
            for key in self.children(entry):
                self.entries.pop(key, None)
                self.excluded.add(key)
            self.loading.discard(entry.key)
        else:
            self.entries.pop(entry.key, None)
            self.excluded.add(entry.key)

    def accept_collection(self, entry: Entry, recordings: list[Entry]):
        self.members[entry.key] = {e.key for e in recordings}
        self.entries.update((e.key, e) for e in recordings if self.allowed(e))
        self.loading.discard(entry.key)

    def contains(self, group: str, key: str) -> bool:
        return (group == key or key in self.members.get(group, set())
                or group in self.parents.get(key, set())
                or group.startswith('tree:') and key.startswith(group.rstrip('/') + '/'))

    def allowed(self, entry):
        if entry.key in self.excluded:
            return False
        for group in self.excluded_groups:
            blocked = self.contains(group, entry.key) or entry.source == 'youtube' and group == 'playlist:' + entry.collection_id
            if blocked:
                # A later explicit child selection overrides an unticked ancestor,
                # without releasing its siblings to an in-flight parent discovery.
                reselected = any(intent != group and self.contains(group, intent)
                                 and self.contains(intent, entry.key) for intent in self.intents)
                if not reselected:
                    return False
        return True
