# Akman Home Movie – Görsel içerik

Akman Home Movie uygulamasının **Görsel** sekmesindeki fotoğraf ve video kanalları bu depodan okunur.

## Kanal ekleme

1. Bu sayfada **Add file > Upload files**'a basın.
2. Dosyaları bilgisayardan sürüklerken klasörüyle birlikte sürükleyin; ya da önce **Add file > Create new file** ile adını `Dağlar/bos.txt` gibi yazarak klasörü oluşturun, sonra o klasörün içine yükleyin.
3. **Commit changes**'e basın.

Bir iki dakika içinde `gorsel.json` kendiliğinden yenilenir. Uygulamada **Ayarlar > Görsel ayarları > Listeyi şimdi yenile** ile hemen görebilirsiniz.

## Kurallar

- **Her klasör bir kanaldır**; kanalın adı klasörün adıdır (örnek: `Dağlar`, `Deniz`, `Şömine`).
- Klasörde fotoğraf (`.jpg`, `.png`, `.webp`) varsa kanal **slayt** olur. Klasöre bir ses dosyası (`.mp3`) koyarsanız slaytın altında çalar.
- Klasörde video (`.mp4`) varsa kanal **dönen video** olur.
- Fotoğraflar yatay ve en çok 1920 piksel genişliğinde olsun; daha büyüğü televizyonu yorar.
- Videolar kısa döngüler olsun (30–90 saniye). GitHub tek dosyada 100 MB'tan büyüğünü kabul etmez; tarayıcıdan yüklemede sınır 25 MB'tır.
- Bu depo herkese açıktır: yalnızca kullanım hakkı serbest içerik koyun, kişisel fotoğraf koymayın.

## Dosyalar

- `gorsel.json`: uygulamanın okuduğu liste. Elle düzenlemeyin; `liste.py` üretir.
- `liste.py` ve `.github/workflows/liste.yml`: listeyi üreten betik ve onu çalıştıran iş.
