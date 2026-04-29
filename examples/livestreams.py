"""
Live stream examples — catalog vs current on-air.

Channel.streams  → /@handle/streams tab: paginated list of all livestream videos
Channel.live     → /@handle/live redirect: the single on-air Video, or None
"""
from tutubo.channel import Channel

url = "https://www.youtube.com/@euronews"
c = Channel(url)

# Check if the channel is currently live
current = c.live   # /@handle/live — one video or None
if current:
    print(f"ON AIR: {current.title}")
    print(f"        {current.watch_url}")
else:
    print("Channel is not currently live.")

# Browse the full streams archive
print("\nRecent livestreams (/@handle/streams tab):")
for v in c.streams:
    status = "LIVE" if v.is_live else "recorded"
    mins = v.length // 60 if v.length else 0
    print(f"  [{status:8s}]  {mins:4d}m  {v.title}")
