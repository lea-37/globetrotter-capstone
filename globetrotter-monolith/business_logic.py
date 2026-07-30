"""
Business Logic Layer
---------------------
Recommendation and trip-planning logic lives here, separate from the
API layer (routing/HTTP concerns) and the data access layer (storage).
This separation is what will make it *possible* (though still work) to
peel this module out into its own microservice in a later phase.
"""

from data_access import get_destinations, get_itineraries_for_user


def recommend_destinations(user, limit=5):
    """
    Very simple scoring model:
      +3 points  if the destination's tags overlap the user's stated preferences
      +2 points  if the destination is in a region the user has already visited
      +popularity_score (0-5), always added, so popular places still surface
      -100 points if the user already has an itinerary there (don't recommend a repeat)
    This is intentionally simple -- Phase 1 cares about having a working,
    explainable pipeline more than a sophisticated algorithm.
    """
    destinations = get_destinations()
    past_itineraries = get_itineraries_for_user(user["id"])
    visited_destination_ids = {it["destination_id"] for it in past_itineraries}
    visited_regions = {
        d["region"] for d in destinations if d["id"] in visited_destination_ids
    }
    preferences = set(user.get("preferences", []))

    scored = []
    for dest in destinations:
        score = dest.get("popularity_score", 0)
        tag_overlap = preferences.intersection(dest.get("tags", []))
        score += 3 * len(tag_overlap)
        if dest["region"] in visited_regions:
            score += 2
        if dest["id"] in visited_destination_ids:
            score -= 100
        scored.append((score, dest))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [dest for score, dest in scored[:limit] if score > -100]


def search_destinations(query=None, tag=None, region=None):
    """Simple in-memory filter over the destinations list."""
    destinations = get_destinations()
    results = destinations

    if query:
        query_lower = query.lower()
        results = [d for d in results if query_lower in d["name"].lower()]
    if tag:
        results = [d for d in results if tag in d.get("tags", [])]
    if region:
        results = [d for d in results if d["region"].lower() == region.lower()]

    return results
