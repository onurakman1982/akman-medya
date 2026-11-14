"""kaynaklar.txt'teki videoları indirir, kısa ve kesintisiz dönen 4K parçalara çevirir.

Satır biçimi:  Kanal adı | video | başlangıç sn | süre sn | ses kaynağı | ses başlangıç sn | tekrar
Son üç alan isteğe bağlı: videonun sesi yoksa başka bir kaynaktan ses alınır,
çok kısa videolar "tekrar" kadar arka arkaya eklenir. Video, depodaki bir dosya da olabilir.
Çıktı: <Kanal adı>/<Kanal adı>.mp4  (dosya zaten varsa yeniden üretilmez)

ONIZLEME=1 ile çalışırsa video üretmez; adaylar.txt'teki her satır için
onizleme/ klasörüne üç karelik bir resim bırakır (hangisinin seçileceğine bakmak için).
"""
import os
import subprocess
import sys

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def rows(path):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = [x.strip() for x in line.split("|")]
        if len(p) >= 4:
            yield p


def run(cmd):
    print(" ".join(cmd[:6]), "...", flush=True)
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def probe(url, entry, stream):
    r = subprocess.run(tool("ffprobe", url) + ["-select_streams", stream,
                        "-show_entries", "stream=" + entry, "-of", "csv=p=0", url],
                       stdout=subprocess.PIPE, text=True)
    return r.stdout.strip().split("\n")[0]


def preview(name, url, start, length):
    os.makedirs("onizleme", exist_ok=True)
    out = os.path.join("onizleme", name + ".jpg")
    step = max(length / 3.0, 1.0)
    r = run(["ffmpeg", "-y", "-v", "error", "-user_agent", UA, "-ss", str(start), "-t", str(length), "-i", url,
             "-vf", "fps=1/%s,scale=640:-2,tile=3x1" % step, "-frames:v", "1", "-q:v", "4", out])
    info = "%s | %s | ses: %s" % (name, probe(url, "width,height,r_frame_rate", "v:0"), probe(url, "codec_name", "a:0") or "yok")
    print(info, r.stdout[-300:], flush=True)
    return info


def tool(name, url):
    # tarayıcı kimliği yalnızca internetten okurken gerekir
    return [name, "-v", "error"] + (["-user_agent", UA] if url.startswith("http") else [])


def make(name, url, start, length, sound_url="", sound_start=0.0, repeat=1):
    out = os.path.join(name, name + ".mp4")
    if os.path.exists(out):
        return True
    os.makedirs(name, exist_ok=True)
    fade = 1.0 if length >= 10 else 0.6
    rate = probe(url, "r_frame_rate", "v:0")
    try:
        a, b = rate.split("/")
        fps = float(a) / float(b)
    except Exception:
        fps = 30.0
    fps = 30 if fps > 31 else round(fps)
    # 4K'dan küçük kaynak büyütülmez; büyütmek ayrıntı katmaz, dosyayı şişirir
    big = (probe(url, "width", "v:0") or "0").isdigit() and int(probe(url, "width", "v:0")) >= 3840
    size = "scale=3840:2160:flags=lanczos," if big else ""
    # ilk bölüm sona bindirilir: son kare ile ilk kare aynı olur, video dönerken sıçramaz
    graph = ("[0:v]fps=%d,%sformat=yuv420p,split[a][b];"
             "[a]trim=start=%s,setpts=PTS-STARTPTS[main];[b]trim=end=%s,setpts=PTS-STARTPTS[head];"
             "[main][head]xfade=transition=fade:duration=%s:offset=%s,format=yuv420p[v]") % (fps, size, fade, fade, fade, length - fade)
    r = run(tool("ffmpeg", url) + ["-y", "-ss", str(start), "-t", str(length + fade), "-i", url,
             "-filter_complex", graph, "-map", "[v]", "-an",
             "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-maxrate", "16M", "-bufsize", "32M",
             "-profile:v", "high", "-level", "5.1", "-g", str(fps * 2), "-movflags", "+faststart", "v.mp4"])
    log = r.stdout[-400:]
    src = sound_url or url
    whole = length * repeat
    has = os.path.exists("v.mp4") and bool(probe(src, "codec_name", "a:0"))
    if has:
        if not sound_url:
            sound_start = start
        r = run(tool("ffmpeg", src) + ["-y", "-ss", str(sound_start), "-t", str(whole + 1.0), "-i", src, "-vn",
                 "-filter_complex", "[0:a]aresample=48000,asetpts=PTS-STARTPTS,asplit[c][d];"
                 "[c]atrim=start=1,asetpts=PTS-STARTPTS,afade=t=out:st=%s:d=1[am];"
                 "[d]atrim=end=1,asetpts=PTS-STARTPTS,afade=t=in:d=1,adelay=%d:all=1[ah];"
                 "[am][ah]amix=inputs=2:normalize=0:duration=first[s]" % (whole - 1, int((whole - 1) * 1000)),
                 "-map", "[s]", "-c:a", "aac", "-b:a", "128k", "-ac", "2", "a.m4a"])
        log += r.stdout[-400:]
        has = os.path.exists("a.m4a")
    if os.path.exists("v.mp4"):
        cmd = ["ffmpeg", "-y", "-v", "error", "-stream_loop", str(repeat - 1), "-i", "v.mp4"]
        cmd += (["-i", "a.m4a", "-map", "0:v", "-map", "1:a", "-shortest"] if has else ["-map", "0:v"])
        r = run(cmd + ["-c", "copy", "-movflags", "+faststart", out])
        log += r.stdout[-400:]
    for t in ("v.mp4", "a.m4a"):
        if os.path.exists(t):
            os.remove(t)
    ok = os.path.exists(out) and os.path.getsize(out) > 200000
    print(name, "tamam %d MB" % (os.path.getsize(out) // 1000000) if ok else "OLMADI", log, flush=True)
    if not ok and os.path.exists(out):
        os.remove(out)
    return ok


def main():
    if os.environ.get("ONIZLEME"):
        notes = [preview(r[0], r[1], float(r[2]), float(r[3])) for r in rows("adaylar.txt")]
        open("onizleme/bilgi.txt", "w", encoding="utf-8").write("\n".join(notes) + "\n")
        return
    bad = []
    for r in rows("kaynaklar.txt"):
        r = r + [""] * (7 - len(r))
        if not make(r[0], r[1], float(r[2]), float(r[3]), r[4], float(r[5] or 0), int(r[6] or 1)):
            bad.append(r[0])
    if bad:
        print("Üretilemeyenler:", ", ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
