"""Show YouTube's 'people also searched for' suggestions and follow one.

Note: YouTube shows related-search cards for broad/lifestyle queries (cooking,
yoga, travel…) but rarely for specific artists/bands. If no suggestions are
found the list will be empty.
"""
from tutubo import YoutubeSearch

s = YoutubeSearch("cooking")

suggestions = []
for q in s.iterate_queries():
    suggestions.append(q)
    if len(suggestions) >= 5:
        break
for i, rs in enumerate(suggestions):
    print(f"[{i}] {rs.query}")

if suggestions:
    chosen = suggestions[0]
    print(f"\nFollowing suggestion: '{chosen.query}'")
    followup = chosen.get()          # returns a new YoutubeSearch
    for v in followup.iterate_videos(max_res=3):
        print(f"  {v.title}  {v.watch_url}")
