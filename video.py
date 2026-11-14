"""kaynaklar.txt'teki videoları indirir, kısa ve kesintisiz dönen 4K parçalara çevirir.

Satır biçimi:  Kanal adı | video adresi | başlangıç saniyesi | süre saniyesi
Çıktı: <Kanal adı>/<Kanal adı>.mp4  (dosya zaten varsa yeniden üretilmez)

ONIZLEME=1 ile çalışırsa video üretmez; adaylar.txt'teki her satır için
onizleme/ klasörüne üç karelik bir resim bırakır (hangisinin seçileceğine bakmak için).
"""
import os
import subprocess
import sys

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
FADE = 1.0  # sondan başa geçişin süresi; dönüş yeri bununla görünmez olur


def rows(path):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = [x.strip() for x in line.split("|")]
        if len(p) >= 4:
            yield p[0], p[1], float(p[2]), float(p[3])


def run(cmd):
    print(" ".join(cmd[:6]), "...", flush=True)
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def probe(url, entry, stream):
    r = subprocess.run(["ffprobe", "-v", "error", "-user_agent", UA, "-select_streams", stream,
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


def make(name, url, start, length):
    out = os.path.join(name, name + ".mp4")
    if os.path.exists(out):
        return True
    os.makedirs(name, exist_ok=True)
    total = length + FADE
    rate = probe(url, "r_frame_rate", "v:0")
    try:
        a, b = rate.split("/")
        fps = float(a) / float(b)
    except Exception:
        fps = 30.0
    fps = 30 if fps > 31 else round(fps)
    sound = bool(probe(url, "codec_name", "a:0"))
    # ilk saniye sona bindirilir: son kare ile ilk kare aynı olur, video dönerken sıçramaz
    graph = ("[0:v]fps=%d,scale=3840:2160:flags=lanczos,format=yuv420p,split[a][b];"
             "[a]trim=start=%s,setpts=PTS-STARTPTS[main];[b]trim=end=%s,setpts=PTS-STARTPTS[head];"
             "[main][head]xfade=transition=fade:duration=%s:offset=%s[v]") % (fps, FADE, FADE, FADE, total - 2 * FADE)
    maps = ["-map", "[v]"]
    if sound:
        graph += (";[0:a]aresample=48000,asplit[c][d];[c]atrim=start=%s,asetpts=PTS-STARTPTS[am];"
                  "[d]atrim=end=%s,asetpts=PTS-STARTPTS[ah];[am][ah]acrossfade=d=%s[s]") % (FADE, FADE, FADE)
        maps += ["-map", "[s]", "-c:a", "aac", "-b:a", "128k", "-ac", "2"]
    r = run(["ffmpeg", "-y", "-v", "error", "-user_agent", UA, "-ss", str(start), "-t", str(total), "-i", url,
             "-filter_complex", graph] + maps +
            ["-c:v", "libx264", "-preset", "fast", "-crf", "21", "-maxrate", "16M", "-bufsize", "32M",
             "-profile:v", "high", "-level", "5.1", "-g", str(fps * 2), "-movflags", "+faststart", out])
    ok = r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 200000
    print(name, "tamam" if ok else "OLMADI", r.stdout[-500:], flush=True)
    if not ok and os.path.exists(out):
        os.remove(out)
    return ok


def main():
    if os.environ.get("ONIZLEME"):
        notes = [preview(*r) for r in rows("adaylar.txt")]
        open("onizleme/bilgi.txt", "w", encoding="utf-8").write("\n".join(notes) + "\n")
        return
    bad = [r[0] for r in rows("kaynaklar.txt") if not make(*r)]
    if bad:
        print("Üretilemeyenler:", ", ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
