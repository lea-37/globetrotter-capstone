"""
Design pattern: STRATEGY
----------------------------------
SORT_STRATEGIES maps a name ("name", "rating", "distance") to a function that
knows how to rank the place list that way. The route just looks up the
strategy the client asked for and applies it — new sort orders can be added
by registering a new function here, with no change to the route code.
"""
import math

from .repositories import PlaceRepository, ReviewRepository

place_repo = PlaceRepository()
review_repo = ReviewRepository()


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def with_rating(place):
    reviews = review_repo.find_by_place(place["id"])
    if reviews:
        avg = sum(r["rating"] for r in reviews) / len(reviews)
    else:
        avg = None
    place = dict(place)
    place["rating"] = round(avg, 1) if avg is not None else None
    place["review_count"] = len(reviews)
    return place


def _sort_by_name(places, **kwargs):
    return sorted(places, key=lambda p: p.get("name", ""))


def _sort_by_rating(places, **kwargs):
    return sorted(places, key=lambda p: (p.get("rating") is None, -(p.get("rating") or 0)))


def _sort_by_distance(places, user_lat=None, user_lon=None, **kwargs):
    if user_lat is None or user_lon is None:
        return places
    return sorted(
        places,
        key=lambda p: _haversine_km(user_lat, user_lon, p["lat"], p["lon"])
    )


SORT_STRATEGIES = {
    "name": _sort_by_name,
    "rating": _sort_by_rating,
    "distance": _sort_by_distance,
}


def list_places(category=None, query=None, sort="name", user_lat=None, user_lon=None):
    places = place_repo.find_by_category(category)
    if query:
        q = query.lower()
        places = [
            p for p in places
            if q in p.get("name", "").lower() or q in p.get("description", "").lower()
        ]
    places = [with_rating(p) for p in places]
    strategy = SORT_STRATEGIES.get(sort, _sort_by_name)
    return strategy(places, user_lat=user_lat, user_lon=user_lon)


def get_place(place_id):
    place = place_repo.find_by_id(place_id)
    if not place:
        return None
    return with_rating(place)
