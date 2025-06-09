from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from .models import TypKolorystyczny, Analiza, ProfilUzytkownika, PlikAnalizy


@admin.register(TypKolorystyczny)
class TypKolorystycznyAdmin(admin.ModelAdmin):
    list_display = ['get_nazwa_display', 'dominujaca_tonacja', 'poziom_kontrastu', 'nasycenie', 'pokaz_kolory']
    list_filter = ['dominujaca_tonacja', 'poziom_kontrastu', 'nasycenie']
    search_fields = ['nazwa', 'opis']
    ordering = ['nazwa']
    
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('nazwa', 'opis')
        }),
        ('Charakterystyki', {
            'fields': ('dominujaca_tonacja', 'poziom_kontrastu', 'nasycenie')
        }),
        ('Paleta kolorów', {
            'fields': ('kolory_podstawowe', 'kolory_unikane'),
            'classes': ('wide',)
        }),
    )
    
    def get_nazwa_display(self, obj):
        return obj.nazwa
    get_nazwa_display.short_description = "Nazwa typu"
    
    def pokaz_kolory(self, obj):
        if obj.kolory_podstawowe:
            html = ""
            for kolor in obj.kolory_podstawowe[:5]:  # Pokaż max 5 kolorów
                html += f'<span style="display:inline-block; width:20px; height:20px; background-color:{kolor}; border:1px solid #ccc; margin:2px;"></span>'
            return format_html(html)
        return "Brak kolorów"
    pokaz_kolory.short_description = "Podgląd kolorów"


class PlikAnalizyInline(admin.TabularInline):
    model = PlikAnalizy
    extra = 0
    readonly_fields = ['rozmiar', 'typ_mime', 'data_uploadu']
    fields = ['plik', 'nazwa_pliku', 'rozmiar', 'typ_mime', 'data_uploadu']


@admin.register(Analiza)
class AnalizaAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'uzytkownik_display', 'uzytkownik_email', 'status', 'typ_kolorystyczny', 'tonacja_skory', 'data_utworzenia']
    list_filter = ['status', 'typ_kolorystyczny', 'tonacja_skory', 'data_utworzenia']
    search_fields = ['uzytkownik__username', 'uzytkownik__email', 'uzytkownik__first_name', 'uzytkownik__last_name']
    readonly_fields = ['data_utworzenia', 'kolory_skory', 'kolory_oczu', 'kolory_wlosow']
    list_per_page = 20
    date_hierarchy = 'data_utworzenia'
    ordering = ['-data_utworzenia']
    
    fieldsets = (
        ('Informacje podstawowe', {
            'fields': ('uzytkownik', 'status', 'data_utworzenia')
        }),
        ('Zdjęcia', {
            'fields': ('zdjecie_nadgarstka', 'zdjecie_oczu', 'zdjecie_wlosow')
        }),
        ('Wyniki analizy', {
            'fields': ('typ_kolorystyczny', 'tonacja_skory', 'kontrast_poziom', 'nasycenie_poziom', 'pewnosc_wyniku')
        }),
        ('Dane kolorów', {
            'fields': ('kolory_skory', 'kolory_oczu', 'kolory_wlosow'),
            'classes': ('collapse',)
        }),
        ('Dodatkowe', {
            'fields': ('notatki',)
        }),
    )
    
    inlines = [PlikAnalizyInline]
    
    actions = ['oznacz_jako_zakonczone', 'oznacz_jako_blad', 'oznacz_jako_oczekujace']
    
    def uzytkownik_display(self, obj):
        return f"{obj.uzytkownik.first_name} {obj.uzytkownik.last_name}" if obj.uzytkownik.first_name else obj.uzytkownik.username
    uzytkownik_display.short_description = "Użytkownik"
    
    def uzytkownik_email(self, obj):
        return obj.uzytkownik.email
    uzytkownik_email.short_description = "Email"
    
    def oznacz_jako_zakonczone(self, request, queryset):
        count = queryset.update(status='completed')
        self.message_user(request, f'{count} analiz oznaczono jako zakończone.')
    oznacz_jako_zakonczone.short_description = "Oznacz wybrane analizy jako zakończone"
    
    def oznacz_jako_blad(self, request, queryset):
        count = queryset.update(status='error')
        self.message_user(request, f'{count} analiz oznaczono jako błędne.')
    oznacz_jako_blad.short_description = "Oznacz wybrane analizy jako błędne"
    
    def oznacz_jako_oczekujace(self, request, queryset):
        count = queryset.update(status='pending')
        self.message_user(request, f'{count} analiz oznaczono jako oczekujące.')
    oznacz_jako_oczekujace.short_description = "Oznacz wybrane analizy jako oczekujące"


@admin.register(ProfilUzytkownika)
class ProfilUzytkownikaAdmin(admin.ModelAdmin):
    list_display = ['uzytkownik_display', 'uzytkownik_email', 'wiek', 'plec', 'ulubiony_typ', 'liczba_analiz', 'data_rejestracji']
    list_filter = ['plec', 'ulubiony_typ', 'data_rejestracji']
    search_fields = ['uzytkownik__username', 'uzytkownik__email', 'uzytkownik__first_name', 'uzytkownik__last_name']
    readonly_fields = ['data_rejestracji', 'liczba_analiz']
    list_per_page = 25
    date_hierarchy = 'data_rejestracji'
    ordering = ['-data_rejestracji']
    
    fieldsets = (
        ('Użytkownik', {
            'fields': ('uzytkownik', 'data_rejestracji')
        }),
        ('Dane osobowe', {
            'fields': ('wiek', 'plec')
        }),
        ('Preferencje', {
            'fields': ('ulubiony_typ',)
        }),
        ('Statystyki', {
            'fields': ('liczba_analiz',)
        }),
    )
    
    def uzytkownik_display(self, obj):
        return f"{obj.uzytkownik.first_name} {obj.uzytkownik.last_name}" if obj.uzytkownik.first_name else obj.uzytkownik.username
    uzytkownik_display.short_description = "Użytkownik"
    
    def uzytkownik_email(self, obj):
        return obj.uzytkownik.email
    uzytkownik_email.short_description = "Email"


@admin.register(PlikAnalizy)
class PlikAnalizyAdmin(admin.ModelAdmin):
    list_display = ['nazwa_pliku', 'analiza_display', 'uzytkownik_display', 'rozmiar_mb', 'typ_mime', 'data_uploadu']
    list_filter = ['typ_mime', 'data_uploadu']
    search_fields = ['nazwa_pliku', 'analiza__uzytkownik__username', 'analiza__uzytkownik__email']
    readonly_fields = ['rozmiar', 'typ_mime', 'data_uploadu']
    date_hierarchy = 'data_uploadu'
    ordering = ['-data_uploadu']
    
    def rozmiar_mb(self, obj):
        return f"{obj.rozmiar / (1024*1024):.2f} MB"
    rozmiar_mb.short_description = "Rozmiar"
    
    def analiza_display(self, obj):
        return str(obj.analiza) if obj.analiza else "Brak analizy"
    analiza_display.short_description = "Analiza"
    
    def uzytkownik_display(self, obj):
        if obj.analiza and obj.analiza.uzytkownik:
            user = obj.analiza.uzytkownik
            return f"{user.first_name} {user.last_name}" if user.first_name else user.username
        return "Brak użytkownika"
    uzytkownik_display.short_description = "Użytkownik"


# Kustomizacja panelu admina
admin.site.site_header = "Color Season - Panel Administracyjny"
admin.site.site_title = "Color Season Admin"
admin.site.index_title = "Zarządzanie aplikacją Color Season"