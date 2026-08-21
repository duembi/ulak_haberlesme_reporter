"""
Mail listesi yönetim aracı.

Kullanım:
  python scripts/mail_yonet.py listele
  python scripts/mail_yonet.py ekle "Ad Soyad" email@ulakhaberlesme.com.tr --rol yonetici
  python scripts/mail_yonet.py durdur email@ulakhaberlesme.com.tr
  python scripts/mail_yonet.py aktifles email@ulakhaberlesme.com.tr
  python scripts/mail_yonet.py sil email@ulakhaberlesme.com.tr
  python scripts/mail_yonet.py test email@ulakhaberlesme.com.tr
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import (
    init_db, mail_ekle, mail_guncelle, mail_sil,
    mail_listesi_tumu, mail_listesi_al,
)


def cmd_listele(args):
    kayitlar = mail_listesi_tumu()
    if not kayitlar:
        print("Mail listesi boş.")
        return

    baslik = f"{'#':<4} {'Ad Soyad':<25} {'E-posta':<35} {'Rol':<12} {'H':<3} {'K':<3} {'E':<3} {'Durum'}"
    print(baslik)
    print("-" * len(baslik))
    for k in kayitlar:
        durum  = "Aktif" if k["aktif"] else "Pasif"
        hafta  = "[OK]" if k["haftalik"] else "-"
        kriz   = "[OK]" if k["kriz"]     else "-"
        hata   = "[OK]" if k["hata"]     else "-"
        print(f"{k['id']:<4} {k['ad_soyad']:<25} {k['email']:<35} "
              f"{k['rol']:<12} {hafta:<3} {kriz:<3} {hata:<3} {durum}")
    print(f"\nToplam: {len(kayitlar)} kayıt  (H=Haftalık, K=Kriz, E=Hata bildirimi)")


def cmd_ekle(args):
    rol = args.rol or "izleyici"
    if rol not in ("yonetici", "izleyici", "teknik"):
        print("Rol 'yonetici', 'izleyici' veya 'teknik' olmalı.")
        sys.exit(1)

    # Yönetici her şeyi alır, teknik sadece hata bildirimini, izleyici haftalık+kriz
    haftalik = rol in ("yonetici", "izleyici")
    kriz     = rol in ("yonetici", "izleyici")
    hata     = rol in ("yonetici", "teknik")

    basari = mail_ekle(args.ad_soyad, args.email, rol, haftalik, kriz, hata)
    if basari:
        print(f"[OK] Eklendi: {args.ad_soyad} <{args.email}> [{rol}]")
    else:
        print(f"Bu e-posta zaten listede: {args.email}")


def cmd_durdur(args):
    if mail_guncelle(args.email, aktif=0):
        print(f"[OK] Pasife alındı: {args.email}")
    else:
        print(f"Bulunamadı: {args.email}")


def cmd_aktifles(args):
    if mail_guncelle(args.email, aktif=1):
        print(f"[OK] Aktife alındı: {args.email}")
    else:
        print(f"Bulunamadı: {args.email}")


def cmd_sil(args):
    onay = input(f"'{args.email}' kalıcı silinecek. Emin misiniz? (e/h): ")
    if onay.lower() == "e":
        if mail_sil(args.email):
            print(f"[OK] Silindi: {args.email}")
        else:
            print(f"Bulunamadı: {args.email}")


def cmd_test(args):
    """Seçilen adrese Resend üzerinden deneme maili gönderir."""
    import resend
    from datetime import datetime
    from config.settings import RESEND_API_KEY, RESEND_FROM

    if not RESEND_API_KEY:
        print("RESEND_API_KEY .env'de tanımlı değil, mail gönderilemez.")
        sys.exit(1)

    alici = args.email
    simdi = datetime.now().strftime("%d.%m.%Y %H:%M")

    html = f"""
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"></head>
<body style="font-family:Calibri,Arial,sans-serif;background:#f4f6f8;margin:0;padding:0">
  <div style="max-width:600px;margin:30px auto;background:#fff;border-radius:8px;
              box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden">
    <div style="background:#1A5276;padding:24px 32px">
      <h1 style="color:#fff;margin:0;font-size:20px">ULAK HABERLEŞME A.Ş.</h1>
      <p style="color:#AED6F1;margin:6px 0 0;font-size:13px">
        Medya Takip Sistemi — Test Maili
      </p>
    </div>
    <div style="padding:28px 32px">
      <p style="color:#2c3e50;font-size:15px;line-height:1.7">
        Merhaba,<br><br>
        Bu, <strong>Ulak Haberleşme Haftalık Medya Takip Sistemi</strong>'nin mail altyapısını doğrulamak
        amacıyla gönderilmiş bir deneme mesajıdır.<br><br>
        Gönderim zamanı: <strong>{simdi}</strong><br>
        Alıcı: <strong>{alici}</strong><br><br>
        Bu maili aldıysanız sistem doğru yapılandırılmış demektir.
      </p>
    </div>
    <div style="background:#EBF5FB;padding:14px 32px;text-align:center">
      <p style="color:#5D6D7E;font-size:12px;margin:0">
        Ulak Haberleşme Medya Takip Sistemi — Otomatik Test
      </p>
    </div>
  </div>
</body>
</html>"""

    resend.api_key = RESEND_API_KEY
    try:
        resend.Emails.send({
            "from":    RESEND_FROM,
            "to":      [alici],
            "subject": f"[TEST] Ulak Haberleşme Mail Sistemi — {simdi}",
            "html":    html,
        })
        print(f"[OK] Test maili gönderildi -> {alici}")
    except Exception as e:
        print(f"[HATA] Gönderilemedi: {e}")


def main():
    init_db()

    parser = argparse.ArgumentParser(description="Ulak Haberleşme mail listesi yönetimi")
    sub = parser.add_subparsers(dest="komut")

    sub.add_parser("listele", help="Tüm alıcıları listele")

    p_ekle = sub.add_parser("ekle", help="Yeni alıcı ekle")
    p_ekle.add_argument("ad_soyad", help="Ad Soyad (tırnak içinde)")
    p_ekle.add_argument("email",    help="E-posta adresi")
    p_ekle.add_argument("--rol", choices=["yonetici", "izleyici", "teknik"],
                        default="izleyici")

    p_dur = sub.add_parser("durdur", help="Alıcıyı pasife al")
    p_dur.add_argument("email")

    p_akt = sub.add_parser("aktifles", help="Alıcıyı tekrar aktife al")
    p_akt.add_argument("email")

    p_sil = sub.add_parser("sil", help="Alıcıyı kalıcı sil")
    p_sil.add_argument("email")

    p_test = sub.add_parser("test", help="Seçilen adrese deneme maili gönder")
    p_test.add_argument("email")

    args = parser.parse_args()

    komutlar = {
        "listele":   cmd_listele,
        "ekle":      cmd_ekle,
        "durdur":    cmd_durdur,
        "aktifles":  cmd_aktifles,
        "sil":       cmd_sil,
        "test":      cmd_test,
    }

    if args.komut in komutlar:
        komutlar[args.komut](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
