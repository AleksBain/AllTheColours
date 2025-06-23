from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from color_analyzer.models import TypKolorystyczny, Analiza, ProfilUzytkownika
from django.utils import timezone
import random
from faker import Faker

fake = Faker('pl_PL')

class Command(BaseCommand):
    help = 'Ładuje fikcyjne dane do bazy'

    def handle(self, *args, **kwargs):
        # Załaduj 12 typów kolorystycznych jeśli ich nie ma
        print("✅ Sprawdzanie typów kolorystycznych...")
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

        for kod, nazwa in SEZONY:
            TypKolorystyczny.objects.get_or_create(
                nazwa=kod,
                defaults={
                    'opis': f"Opis typu {nazwa}",
                    'dominujaca_tonacja': random.choice(['ciepła', 'chłodna']),
                    'poziom_kontrastu': random.choice(['niski', 'średni', 'wysoki']),
                    'nasycenie': random.choice(['niskie', 'średnie', 'wysokie']),
                    'kolory_podstawowe': ['#ffccaa', '#336699'],
                    'kolory_unikane': ['#000000', '#ffffff'],
                }
            )
        print("✅ Typy kolorystyczne gotowe.")

        # Tworzenie użytkowników
        print("👤 Tworzenie użytkowników i profili...")
        for i in range(15):
            username = f"user{i}"
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, password='test1234')
                ProfilUzytkownika.objects.create(
                    uzytkownik=user,
                    wiek=random.randint(18, 65),
                    plec=random.choice(['K', 'M']),
                    ulubiony_typ=TypKolorystyczny.objects.order_by('?').first()
                )
        print("✅ Użytkownicy stworzeni.")

        # Tworzenie analiz
        print("🧪 Tworzenie analiz...")
        uzytkownicy = User.objects.all()
        typy = list(TypKolorystyczny.objects.all())

        for _ in range(60):
            user = random.choice(uzytkownicy)
            typ = random.choice(typy)
            Analiza.objects.create(
                uzytkownik=user,
                status='completed',
                data_utworzenia=fake.date_time_between(start_date='-1y', end_date='now', tzinfo=timezone.get_current_timezone()),
                typ_kolorystyczny=typ,
                tonacja_skory=typ.dominujaca_tonacja,
                kontrast_poziom=random.randint(1, 10),
                nasycenie_poziom=random.randint(1, 10),
                kolory_skory=["#fceee4", "#fcd2b0"],
                kolory_oczu=["#123456", "#abcdef"],
                kolory_wlosow=["#111111", "#333333"],
                pewnosc_wyniku=round(random.uniform(0.6, 0.99), 2),
                notatki=fake.sentence()
            )
        print("✅ Analizy dodane.")
