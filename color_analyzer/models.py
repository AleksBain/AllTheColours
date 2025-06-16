from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TypKolorystyczny(models.Model):
    SEZONY = [
        ('spring_light', 'Jasna Wiosna'),
        ('spring_warm', 'Ciepła Wiosna'),
        ('spring_clear', 'Czysta Wiosna'),
        ('summer_light', 'Jasne Lato'),
        ('summer_cool', 'Chłodne Lato'),
        ('summer_soft', 'Miękkie Lato'),
        ('autumn_soft', 'Miękka Jesień'),
        ('autumn_warm', 'Ciepła Jesień'),
        ('autumn_deep', 'Głęboka Jesień'),
        ('winter_cool', 'Chłodna Zima'),
        ('winter_clear', 'Czysta Zima'),
        ('winter_deep', 'Głęboka Zima'),
    ]
    nazwa = models.CharField(max_length=50, choices=SEZONY, unique=True)
    opis = models.TextField()
    dominujaca_tonacja = models.CharField(max_length=20)
    poziom_kontrastu = models.CharField(max_length=20)
    nasycenie = models.CharField(max_length=20)
    kolory_podstawowe = models.JSONField(default=list)
    kolory_unikane = models.JSONField(default=list)

    class Meta:
        verbose_name = "Typ Kolorystyczny"
        verbose_name_plural = "Typy Kolorystyczne"

    def __str__(self):
        return self.get_nazwa_display()

class Analiza(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Oczekuje'),
        ('processing', 'Przetwarzanie'),
        ('completed', 'Zakończona'),
        ('error', 'Błąd'),
    ]
    uzytkownik = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analizy')
    data_utworzenia = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    zdjecie_nadgarstka = models.ImageField(upload_to='analizy/nadgarstki/')
    zdjecie_oczu = models.ImageField(upload_to='analizy/oczy/')
    zdjecie_wlosow = models.ImageField(upload_to='analizy/wlosy/')
    typ_kolorystyczny = models.ForeignKey(TypKolorystyczny, on_delete=models.SET_NULL, null=True, blank=True)
    tonacja_skory = models.CharField(max_length=20, blank=True)
    kontrast_poziom = models.IntegerField(null=True, blank=True)
    nasycenie_poziom = models.IntegerField(null=True, blank=True)
    kolory_skory = models.JSONField(default=list)
    kolory_oczu = models.JSONField(default=list)
    kolory_wlosow = models.JSONField(default=list)
    notatki = models.TextField(blank=True)
    pewnosc_wyniku = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Analiza"
        verbose_name_plural = "Analizy"
        ordering = ['-data_utworzenia']

    def __str__(self):
        return f"Analiza {self.uzytkownik.username} - {self.data_utworzenia.strftime('%Y.%m.%d')}"

class ProfilUzytkownika(models.Model):
    PLEC_CHOICES = [
        ('K', 'Kobieta'),
        ('M', 'Mężczyzna'),
        ('N', 'Nie podano'),
    ]
    uzytkownik = models.OneToOneField(User, on_delete=models.CASCADE)
    wiek = models.IntegerField(null=True, blank=True)
    plec = models.CharField(max_length=1, choices=PLEC_CHOICES, default='N')
    data_rejestracji = models.DateTimeField(default=timezone.now)
    ulubiony_typ = models.ForeignKey(TypKolorystyczny, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Profil Użytkownika"
        verbose_name_plural = "Profile Użytkowników"

    def __str__(self):
        return f"Profil {self.uzytkownik.username}"

    @property
    def liczba_analiz(self):
        return self.uzytkownik.analizy.count()

class PlikAnalizy(models.Model):
    analiza = models.ForeignKey(Analiza, on_delete=models.CASCADE, related_name='pliki')
    nazwa_pliku = models.CharField(max_length=255)
    plik = models.FileField(upload_to='analizy/pliki/')
    rozmiar = models.IntegerField()
    typ_mime = models.CharField(max_length=100)
    data_uploadu = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Plik Analizy"
        verbose_name_plural = "Pliki Analiz"

    def __str__(self):
        return f"{self.nazwa_pliku} - {self.analiza}"