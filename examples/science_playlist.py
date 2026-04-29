"""
Build a personal science playlist from PBS and Kurzgesagt.

Channels: @pbsspacetime, @pbsinfiniteseries, @eons, @kurzgesagt, @knowledgia
Filters by topic keyword and sorts by view count.
"""
from tutubo.channel import Channel

CHANNELS = [
    ("PBS Space Time",      "https://www.youtube.com/@pbsspacetime/videos"),
    ("PBS Infinite Series", "https://www.youtube.com/@pbsinfiniteseries/videos"),
    ("Eons",                "https://www.youtube.com/@eons/videos"),
    ("Kurzgesagt",          "https://www.youtube.com/@kurzgesagt/videos"),
    ("Knowledgia",          "https://www.youtube.com/@knowledgia/videos"),
]

TOPIC = "evolution"   # change to any topic you want

print(f'Science videos matching "{TOPIC}"\n' + "─" * 60)

hits = []
for name, url in CHANNELS:
    c = Channel(url)
    channel_hits = 0
    for v in c.videos:
        if TOPIC.lower() not in (v.title or "").lower():
            continue
        try:
            views = int(''.join(c for c in str(v.view_count) if c.isdigit()) or 0)
        except Exception:
            views = 0
        hits.append((views, name, v))
        channel_hits += 1
        if channel_hits >= 5:
            break

hits.sort(reverse=True)
for views, channel, v in hits[:20]:
    print(f"  {views:>10,}  views  [{channel}]")
    print(f"  {v.title}")
    print(f"  {v.watch_url}\n")
