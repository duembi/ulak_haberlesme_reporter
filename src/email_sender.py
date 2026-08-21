"""
E-posta gönderim modülü — Resend API kullanır.
RESEND_API_KEY .env dosyasından okunur; tanımlı değilse gönderim sessizce atlanır.
"""
import base64
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

import resend
from loguru import logger

from config.settings import EMAIL_TO, RESEND_API_KEY, RESEND_FROM
from src.news_fetcher import Haber
from src.database import mail_listesi_al


def _alicilari_al(tur: str) -> list[str]:
    """DB'den aktif alıcıları çeker; DB boşsa .env'deki EMAIL_TO'ya döner."""
    try:
        kayitlar = mail_listesi_al(tur)
        if kayitlar:
            return [k["email"] for k in kayitlar]
    except Exception:
        pass
    return EMAIL_TO


def _html_govde(haberler: list[Haber], yonetici_ozeti: str, rapor_tarihi: datetime) -> str:
    sayim = Counter(h.sentiment for h in haberler)
    toplam = len(haberler)

    def oran(s):
        return f"%{sayim.get(s, 0) / toplam * 100:.0f}" if toplam else "%-"

    sentiment_satirlari = ""
    for sentiment, renk in [("olumlu", "#1E8449"), ("olumsuz", "#C0392B"), ("nötr", "#5D6D7E")]:
        sayi = sayim.get(sentiment, 0)
        sentiment_satirlari += f"""
        <tr>
          <td style="padding:8px 12px;color:{renk};font-weight:bold">{sentiment.capitalize()}</td>
          <td style="padding:8px 12px;text-align:center">{sayi}</td>
          <td style="padding:8px 12px;text-align:center">{oran(sentiment)}</td>
        </tr>"""

    ozet_paragraflari = "".join(
        f"<p style='margin:0 0 10px'>{p.strip()}</p>"
        for p in yonetici_ozeti.split("\n") if p.strip()
    )

    return f"""
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"></head>
<body style="font-family:Calibri,Arial,sans-serif;background:#f4f6f8;margin:0;padding:0">
  <div style="max-width:680px;margin:30px auto;background:#fff;border-radius:8px;
              box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden">

    <div style="background:#1A5276;padding:28px 32px">
      <h1 style="color:#fff;margin:0;font-size:22px">ULAK HABERLEŞME A.Ş.</h1>
      <p style="color:#AED6F1;margin:6px 0 0;font-size:14px">
        Haftalık Medya Takip Raporu — {rapor_tarihi.strftime('%d.%m.%Y')}
      </p>
    </div>

    <div style="padding:28px 32px">
      <h2 style="color:#1A5276;font-size:16px;margin:0 0 14px;
                 border-bottom:2px solid #AED6F1;padding-bottom:6px">Yönetici Özeti</h2>
      <div style="color:#2c3e50;font-size:14px;line-height:1.7">
        {ozet_paragraflari}
      </div>
    </div>

    <div style="padding:0 32px 28px">
      <h2 style="color:#1A5276;font-size:16px;margin:0 0 14px;
                 border-bottom:2px solid #AED6F1;padding-bottom:6px">
        Sentiment Dağılımı ({toplam} haber)
      </h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead>
          <tr style="background:#1A5276;color:#fff">
            <th style="padding:10px 12px;text-align:left">Sentiment</th>
            <th style="padding:10px 12px;text-align:center">Haber</th>
            <th style="padding:10px 12px;text-align:center">Oran</th>
          </tr>
        </thead>
        <tbody>{sentiment_satirlari}</tbody>
      </table>
    </div>

    <div style="background:#EBF5FB;padding:16px 32px;text-align:center">
      <p style="color:#5D6D7E;font-size:12px;margin:0">
        Bu rapor otomatik olarak üretilmiştir. Detaylar için ekteki PDF'i inceleyiniz.
      </p>
    </div>
  </div>
</body>
</html>"""


def _resend_gonder(konu: str, html: str, alicilar: list[str],
                   ekler: list[dict] | None = None) -> bool:
    """Resend API üzerinden e-posta gönderir."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY tanımlı değil, e-posta gönderimi atlanıyor")
        return False
    if not alicilar:
        return False

    resend.api_key = RESEND_API_KEY
    params: dict = {
        "from":    RESEND_FROM,
        "to":      alicilar,
        "subject": konu,
        "html":    html,
    }
    if ekler:
        params["attachments"] = ekler

    try:
        resend.Emails.send(params)
        logger.info(f"E-posta gönderildi -> {', '.join(alicilar)}")
        return True
    except Exception as e:
        logger.error(f"Resend hatası: {e}")
        return False


def rapor_gonder(pdf_yolu: Path, haberler: list[Haber], yonetici_ozeti: str) -> bool:
    """Haftalık raporu PDF eki ile gönderir."""
    alicilar = _alicilari_al("haftalik")
    if not alicilar:
        logger.warning("Haftalık rapor için alıcı bulunamadı")
        return False

    simdi = datetime.now()
    konu  = f"Ulak Haberleşme Haftalık Medya Raporu — {simdi.strftime('%d.%m.%Y')}"
    html  = _html_govde(haberler, yonetici_ozeti, simdi)

    ekler = []
    if pdf_yolu.exists():
        with open(pdf_yolu, "rb") as f:
            ekler = [{"filename": pdf_yolu.name, "content": base64.b64encode(f.read()).decode()}]

    return _resend_gonder(konu, html, alicilar, ekler or None)


def hata_bildir(hata: Exception, adim: str, sure_sn: float | None = None) -> bool:
    """Pipeline hatası oluştuğunda uyarı e-postası gönderir."""
    simdi   = datetime.now()
    tb_text = traceback.format_exc().replace("\n", "<br>").replace(" ", "&nbsp;")
    sure_str = f"{sure_sn:.0f} sn" if sure_sn is not None else "?"

    html = f"""
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"></head>
<body style="font-family:Calibri,Arial,sans-serif;background:#f4f6f8;margin:0;padding:0">
  <div style="max-width:680px;margin:30px auto;background:#fff;border-radius:8px;
              box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden">
    <div style="background:#922B21;padding:24px 32px">
      <h1 style="color:#fff;margin:0;font-size:20px">ULAK HABERLEŞME — Pipeline Hatası</h1>
      <p style="color:#F5B7B1;margin:6px 0 0;font-size:13px">
        {simdi.strftime('%d.%m.%Y %H:%M')} &nbsp;|&nbsp; Çalışma süresi: {sure_str}
      </p>
    </div>
    <div style="padding:24px 32px">
      <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:20px">
        <tr style="background:#F9EBEA">
          <td style="padding:10px 14px;font-weight:bold;width:120px;color:#922B21">Hata adımı</td>
          <td style="padding:10px 14px;color:#2c3e50">{adim}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;font-weight:bold;color:#922B21">Hata türü</td>
          <td style="padding:10px 14px;color:#2c3e50">{type(hata).__name__}</td>
        </tr>
        <tr style="background:#F9EBEA">
          <td style="padding:10px 14px;font-weight:bold;color:#922B21">Mesaj</td>
          <td style="padding:10px 14px;color:#2c3e50">{str(hata)[:300]}</td>
        </tr>
      </table>
      <details>
        <summary style="cursor:pointer;color:#922B21;font-size:13px">Traceback (tıkla)</summary>
        <pre style="background:#FEF9E7;padding:12px;font-size:12px;overflow-x:auto;
                    border-radius:4px;margin-top:8px">{tb_text}</pre>
      </details>
    </div>
    <div style="background:#EBF5FB;padding:14px 32px;text-align:center">
      <p style="color:#5D6D7E;font-size:12px;margin:0">
        Otomatik hata bildirimi — Ulak Haberleşme Medya Takip Sistemi
      </p>
    </div>
  </div>
</body>
</html>"""

    konu     = f"[HATA] Ulak Haberleşme Pipeline — {adim} — {simdi.strftime('%d.%m.%Y %H:%M')}"
    alicilar = _alicilari_al("hata")
    sonuc    = _resend_gonder(konu, html, alicilar)
    if sonuc:
        logger.info(f"Hata bildirimi gönderildi -> {', '.join(alicilar)}")
    return sonuc


def kriz_bildir(seviye: str, aciklama: str, haberler: list[Haber]) -> bool:
    """Kriz veya dikkat seviyesinde uyarı e-postası gönderir."""
    simdi  = datetime.now()
    renk   = "#922B21" if seviye == "kriz" else "#9A7D0A"
    etiket = "KRİZ" if seviye == "kriz" else "DİKKAT"

    olumsuz = [h for h in haberler if h.sentiment == "olumsuz"]
    haber_satirlari = "".join(
        f"<tr{'style=\"background:#F9EBEA\"' if i % 2 == 0 else ''}>"
        f"<td style='padding:8px 12px;font-size:13px'>"
        f"{'📅 ' + h.tarih.strftime('%d.%m.%Y') if h.tarih else '📅 ?'}"
        f"</td>"
        f"<td style='padding:8px 12px;font-size:13px'>{h.baslik[:90]}</td>"
        f"</tr>"
        for i, h in enumerate(olumsuz[:10])
    )
    aciklama_html = aciklama.replace("\n", "<br>")

    html = f"""
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"></head>
<body style="font-family:Calibri,Arial,sans-serif;background:#f4f6f8;margin:0;padding:0">
  <div style="max-width:680px;margin:30px auto;background:#fff;border-radius:8px;
              box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden">
    <div style="background:{renk};padding:24px 32px">
      <h1 style="color:#fff;margin:0;font-size:20px">
        ULAK HABERLEŞME — Medya {etiket} Uyarısı
      </h1>
      <p style="color:#FADBD8;margin:6px 0 0;font-size:13px">
        {simdi.strftime('%d.%m.%Y %H:%M')}
      </p>
    </div>
    <div style="padding:24px 32px">
      <div style="background:#F9EBEA;border-left:4px solid {renk};
                  padding:14px 18px;border-radius:0 4px 4px 0;margin-bottom:20px;
                  font-size:14px;color:#2c3e50;line-height:1.6">
        {aciklama_html}
      </div>
      {"<h3 style='color:#1A5276;font-size:15px;margin:0 0 10px'>Olumsuz Haberler</h3><table style='width:100%;border-collapse:collapse'>" + haber_satirlari + "</table>" if haber_satirlari else ""}
    </div>
    <div style="background:#EBF5FB;padding:14px 32px;text-align:center">
      <p style="color:#5D6D7E;font-size:12px;margin:0">
        Otomatik kriz uyarısı — Ulak Haberleşme Medya Takip Sistemi
      </p>
    </div>
  </div>
</body>
</html>"""

    konu     = f"[{etiket}] Ulak Haberleşme Medya Uyarısı — {simdi.strftime('%d.%m.%Y %H:%M')}"
    alicilar = _alicilari_al("kriz")
    sonuc    = _resend_gonder(konu, html, alicilar)
    if sonuc:
        logger.info(f"Kriz bildirimi gönderildi -> {', '.join(alicilar)}")
    return sonuc
