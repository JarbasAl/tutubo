"""List podcast shows on a channel and the first few episodes of each."""
from tutubo.channel import Channel

c = Channel("https://www.youtube.com/@TheDissenterRL")
print(f"Channel: {c.channel_name}\n")

for pod in c.podcasts:
    print(f"{pod.title} — {pod.episode_count}")
    pl = pod.get()
    count = 0
    for ep in pl.videos:
        print(f"  {ep.watch_url}")
        count += 1
        if count >= 3:
            break
    print()
