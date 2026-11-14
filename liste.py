"""Klasörlerdeki fotoğraf, video ve seslerden gorsel.json listesini üretir.

Her klasör bir kanaldır; kanalın adı klasörün adıdır.
- Klasörde fotoğraf varsa: slayt kanalı. Klasördeki ilk ses dosyası slaytın altında çalar.
- Klasörde video varsa: her video ayrı bir kanal olur (tek video varsa adı klasörün adıdır).
"""
import json
import os
from urllib.parse import quote

BASE = "https://raw.githubusercontent.com/onurakman1982/akman-medya/main/"
IMAGES = (".jpg", ".jpeg", ".png", ".webp")
VIDEOS = (".mp4", ".m4v", ".webm", ".mkv")
SOUNDS = (".mp3", ".m4a", ".aac", ".ogg")
SKIP = ("kaynak", "onizleme")  # ham dosyalar ve önizlemeler kanal değildir


def url(path):
    return BASE + quote(path.replace(os.sep, "/"))


def main():
    channels = []
    for folder in sorted(os.listdir("."), key=str.lower):
        if folder.startswith(".") or folder in SKIP or not os.path.isdir(folder):
            continue
        files = sorted(os.listdir(folder), key=str.lower)
        pick = lambda exts: [os.path.join(folder, f) for f in files if f.lower().endswith(exts)]
        images, videos, sounds = pick(IMAGES), pick(VIDEOS), pick(SOUNDS)
        for v in videos:
            name = folder if len(videos) == 1 else folder + " - " + os.path.splitext(os.path.basename(v))[0]
            channels.append({"ad": name, "tur": "video", "video": url(v)})
        if images:
            ch = {"ad": folder, "tur": "slayt", "resimler": [url(i) for i in images]}
            if sounds:
                ch["ses"] = url(sounds[0])
            channels.append(ch)
    with open("gorsel.json", "w", encoding="utf-8") as f:
        json.dump({"surum": 1, "kanallar": channels}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(len(channels), "kanal yazıldı")


if __name__ == "__main__":
    main()
