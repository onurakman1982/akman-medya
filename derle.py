"""derleme.txt'teki kısa videoları indirir, arka arkaya ekleyip tek bir kanal videosu yapar.

Satır biçimi:  Kanal adı | parça adı | video adresi | yedek adres (isteğe bağlı)
Aynı kanal adını taşıyan satırlar yazıldıkları sırayla birleştirilir.
Çıktı: <Kanal adı>/<Kanal adı>.mp4  (dosya zaten varsa yeniden üretilmez)
"""
import os
import subprocess
import sys

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
LIMIT = 90 * 1000 * 1000  # depo tek dosyada 100 MB'tan büyüğünü kabul etmez


def sh(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout


def probe(path, entry, stream=None):
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", entry, "-of", "csv=p=0", path]
    return sh(cmd)[1].strip().split("\n")[0]


def fetch(urls, out):
    for u in urls:
        code, log = sh(["curl", "-sSL", "--fail", "-A", UA, "-e", "https://mixkit.co/", "-o", out, u])
        ok = code == 0 and os.path.exists(out) and os.path.getsize(out) > 300000 and probe(out, "stream=codec_name", "v:0")
        print("indir", u, "tamam" if ok else "olmadı " + log[-200:], flush=True)
        if ok:
            return True
    return False


def part(src, out, rate):
    """Parçayı ortak ölçüye getirir; başı ve sonu yumuşak açılıp kapanır, sesi yoksa sessiz iz eklenir."""
    dur = float(probe(src, "format=duration") or 0)
    if dur < 2:
        return 0
    sound = bool(probe(src, "stream=codec_name", "a:0"))
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p,"
          "fade=t=in:d=0.6,fade=t=out:st=%.2f:d=0.6") % (dur - 0.6)
    af = "aresample=48000,afade=t=in:d=0.6,afade=t=out:st=%.2f:d=0.6" % (dur - 0.6)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src]
    if not sound:
        cmd += ["-f", "lavfi", "-t", "%.2f" % dur, "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-map", "0:v:0", "-map", "0:a:0" if sound else "1:a:0", "-vf", vf]
    if sound:
        cmd += ["-af", af]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", rate, "-bufsize", "12M", "-profile:v", "high",
            "-g", "60", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-shortest", "-video_track_timescale", "30000", out]
    code, log = sh(cmd)
    if code != 0:
        print("parça olmadı", log[-300:], flush=True)
        return 0
    return dur


def build(name, rows, rate):
    parts, notes, total = [], [], 0.0
    for n, (title, urls) in enumerate(rows):
        raw, cut = "ham%d.mp4" % n, "p%d.mp4" % n
        if not fetch(urls, raw):
            notes.append(title + ": indirilemedi")
            continue
        size = probe(raw, "stream=width,height", "v:0")
        d = part(raw, cut, rate)
        os.remove(raw)
        if d:
            parts.append(cut)
            notes.append("%s: %s, %.0f sn" % (title, size, d))
            total += d
    if not parts:
        return None, notes, 0
    with open("sira.txt", "w") as f:
        for p in parts:
            f.write("file '%s'\n" % p)
    os.makedirs(name, exist_ok=True)
    out = os.path.join(name, name + ".mp4")
    code, log = sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "sira.txt", "-c", "copy", "-movflags", "+faststart", out])
    for p in parts + ["sira.txt"]:
        os.remove(p)
    if code != 0:
        print("birleştirme olmadı", log[-300:], flush=True)
        return None, notes, total
    return out, notes, total


def main():
    groups = {}
    for line in open("derleme.txt", encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = [x.strip() for x in line.split("|")]
        if len(p) >= 3:
            groups.setdefault(p[0], []).append((p[1], [u for u in p[2:] if u]))
    bad = False
    for name, rows in groups.items():
        if os.path.exists(os.path.join(name, name + ".mp4")):
            continue
        out, notes, total = build(name, rows, "8M")
        if out and os.path.getsize(out) > LIMIT:
            # dosya sınırı aşıyorsa süreye göre daha düşük hızla baştan üretilir
            os.remove(out)
            out, notes, total = build(name, rows, "%dk" % int(LIMIT * 8 / max(total, 1) / 1000 * 0.85 - 128))
        print(name, "\n  " + "\n  ".join(notes), flush=True)
        if out:
            print(name, "tamam: %d MB, %.0f sn" % (os.path.getsize(out) // 1000000, total), flush=True)
            open(os.path.join(name, "icindekiler.txt"), "w", encoding="utf-8").write("\n".join(notes) + "\n")
        else:
            bad = True
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
