"""
Design pattern: REPOSITORY
----------------------------------
Each Repository class is the only thing in the app allowed to know that
"the database" is a JSON file. Routes and services call repository methods
(find_all, find_by_id, add, ...) and never touch JSONStore or the filesystem
directly. If the JSON file storage is later swapped for a real database
(Phase 2+ of the capstone), only this file needs to change.
"""
import os
from .store import JSONStore

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class BaseRepository:
    filename = None

    def __init__(self):
        self.store = JSONStore.instance(os.path.join(DATA_DIR, self.filename))

    def find_all(self):
        return self.store.read()

    def find_by_id(self, item_id):
        return next((row for row in self.find_all() if row.get("id") == item_id), None)

    def add(self, row):
        data = self.find_all()
        row["id"] = self.store.next_id(data)
        data.append(row)
        self.store.write(data)
        return row


class UserRepository(BaseRepository):
    filename = "users.json"

    def find_by_email(self, email):
        email = (email or "").strip().lower()
        return next((u for u in self.find_all() if u.get("email", "").lower() == email), None)


class PlaceRepository(BaseRepository):
    filename = "places.json"

    def find_by_category(self, category):
        if not category:
            return self.find_all()
        category = category.lower()
        return [p for p in self.find_all() if p.get("category", "").lower() == category]

    def search(self, query):
        if not query:
            return self.find_all()
        q = query.lower()
        return [
            p for p in self.find_all()
            if q in p.get("name", "").lower()
            or q in p.get("description", "").lower()
            or q in p.get("address", "").lower()
        ]


class ReviewRepository(BaseRepository):
    filename = "reviews.json"

    def find_by_place(self, place_id):
        return [r for r in self.find_all() if r.get("place_id") == place_id]
