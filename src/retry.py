"""
Exponential backoff retry decorator.
Geçici ağ/API hatalarında otomatik tekrar dener.
"""
import time
import functools
from loguru import logger


def retry(max_deneme: int = 3, bekleme: float = 2.0, carpan: float = 2.0,
          istisnalar: tuple = (Exception,)):
    """
    Decorator — fonksiyon hata verirse exponential backoff ile tekrar dener.

    max_deneme : toplam deneme sayısı
    bekleme    : ilk bekleme süresi (saniye)
    carpan     : her denemede bekleme süresini çarp
    istisnalar : yakalanacak hata türleri
    """
    def dekorator(func):
        @functools.wraps(func)
        def sarmalayici(*args, **kwargs):
            sure = bekleme
            for deneme in range(1, max_deneme + 1):
                try:
                    return func(*args, **kwargs)
                except istisnalar as e:
                    if deneme == max_deneme:
                        logger.error(
                            f"{func.__name__} {max_deneme} denemede başarısız: {e}"
                        )
                        raise
                    logger.warning(
                        f"{func.__name__} hata (deneme {deneme}/{max_deneme}): {e} "
                        f"— {sure:.0f}s sonra tekrar"
                    )
                    time.sleep(sure)
                    sure *= carpan
        return sarmalayici
    return dekorator
