import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend bez GUI
import matplotlib.pyplot as plt
from colorthief import ColorThief
from sklearn.cluster import KMeans
import json
import base64
from io import BytesIO


def pobierz_dominujace_kolory(sciezka_obrazu, liczba_kolorow=5):
    """Pobiera dominujące kolory z obrazu"""
    try:
        color_thief = ColorThief(sciezka_obrazu)
        palette = color_thief.get_palette(color_count=liczba_kolorow)
        
        # Konwertuj na hex
        hex_kolory = []
        for rgb in palette:
            hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
            hex_kolory.append(hex_color)
        
        return hex_kolory
    except Exception as e:
        print(f"Błąd pobierania kolorów: {e}")
        return ['#000000']  # Fallback


def analizuj_kolory(kolory_skory, kolory_oczu, kolory_wlosow):
    """Analizuje kolory i określa charakterystyki"""
    
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hsv(rgb):
        r, g, b = [x/255.0 for x in rgb]
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        
        if diff == 0:
            h = 0
        elif max_val == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_val == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360
        
        s = 0 if max_val == 0 else diff / max_val
        v = max_val
        
        return h, s, v
    
    def okresl_tonacje(hex_kolory):
        """Określa czy kolory są ciepłe czy zimne"""
        ciepla_count = 0
        zimna_count = 0
        
        for hex_color in hex_kolory:
            rgb = hex_to_rgb(hex_color)
            h, s, v = rgb_to_hsv(rgb)
            
            # Ciepłe: 0-60° (czerwień-żółty) i 300-360° (magenta-czerwień)
            # Zimne: 60-300° (żółty-zielony-niebieski-magenta)
            if (0 <= h <= 60) or (300 <= h <= 360):
                ciepla_count += 1
            else:
                zimna_count += 1
        
        return 'ciepła' if ciepla_count > zimna_count else 'zimna'
    
    def oblicz_kontrast(kolory_skory, kolory_wlosow, kolory_oczu):
        """Oblicza poziom kontrastu między kolorami"""
        def luminancja(hex_color):
            rgb = hex_to_rgb(hex_color)
            # Formuła luminancji względnej
            r, g, b = [x/255.0 for x in rgb]
            return 0.299 * r + 0.587 * g + 0.114 * b
        
        lum_skora = np.mean([luminancja(c) for c in kolory_skory])
        lum_wlosy = np.mean([luminancja(c) for c in kolory_wlosow])
        lum_oczy = np.mean([luminancja(c) for c in kolory_oczu])
        
        # Kontrast między skórą a włosami
        kontrast_wlosy = abs(lum_skora - lum_wlosy)
        # Kontrast między skórą a oczami
        kontrast_oczy = abs(lum_skora - lum_oczy)
        
        # Średni kontrast na skali 1-10
        sredni_kontrast = (kontrast_wlosy + kontrast_oczy) / 2
        return min(10, max(1, int(sredni_kontrast * 10)))
    
    def oblicz_nasycenie(wszystkie_kolory):
        """Oblicza poziom nasycenia kolorów"""
        nasycenia = []
        for hex_color in wszystkie_kolory:
            rgb = hex_to_rgb(hex_color)
            h, s, v = rgb_to_hsv(rgb)
            nasycenia.append(s)
        
        srednie_nasycenie = np.mean(nasycenia)
        return min(10, max(1, int(srednie_nasycenie * 10)))
    
    # Główna analiza
    wszystkie_kolory = kolory_skory + kolory_oczu + kolory_wlosow
    
    tonacja = okresl_tonacje(wszystkie_kolory)
    kontrast = oblicz_kontrast(kolory_skory, kolory_wlosow, kolory_oczu)
    nasycenie = oblicz_nasycenie(wszystkie_kolory)
    
    # Pewność wyniku (uproszczona)
    pewnosc = min(1.0, (kontrast + nasycenie) / 20.0 + 0.5)
    
    return {
        'tonacja': tonacja,
        'kontrast': kontrast,
        'nasycenie': nasycenie,
        'pewnosc': pewnosc
    }


def generuj_wykres_kolorow(analiza):
    """Generuje wykres kolorów dla analizy"""
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Wykres 1: Kolory skóry
        if analiza.kolory_skory:
            kolory_skory = [k for k in analiza.kolory_skory if k]
            if kolory_skory:
                axes[0, 0].pie([1] * len(kolory_skory), colors=kolory_skory, startangle=90)
                axes[0, 0].set_title('Kolory skóry')
        
        # Wykres 2: Kolory oczu
        if analiza.kolory_oczu:
            kolory_oczu = [k for k in analiza.kolory_oczu if k]
            if kolory_oczu:
                axes[0, 1].pie([1] * len(kolory_oczu), colors=kolory_oczu, startangle=90)
                axes[0, 1].set_title('Kolory oczu')
        
        # Wykres 3: Kolory włosów
        if analiza.kolory_wlosow:
            kolory_wlosow = [k for k in analiza.kolory_wlosow if k]
            if kolory_wlosow:
                axes[1, 0].pie([1] * len(kolory_wlosow), colors=kolory_wlosow, startangle=90)
                axes[1, 0].set_title('Kolory włosów')
        
        # Wykres 4: Paleta typu kolorystycznego
        if analiza.typ_kolorystyczny and analiza.typ_kolorystyczny.kolory_podstawowe:
            paleta = analiza.typ_kolorystyczny.kolory_podstawowe
            axes[1, 1].pie([1] * len(paleta), colors=paleta, startangle=90)
            axes[1, 1].set_title(f'Paleta {analiza.typ_kolorystyczny.get_nazwa_display()}')
        
        plt.tight_layout()
        
        # Konwertuj do base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close()
        
        graphic = base64.b64encode(image_png).decode('utf-8')
        
        return {
            'image': graphic,
            'type': 'png'
        }
        
    except Exception as e:
        return {'error': str(e)}


def generuj_koło_kolorow():
    """Generuje koło kolorów dla wizualizacji"""
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    # Generuj kolory dla koła
    theta = np.linspace(0, 2*np.pi, 360)
    radius = np.ones_like(theta)
    
    # Utwórz kolory HSV
    colors = []
    for angle in theta:
        hue = angle / (2 * np.pi)
        colors.append(plt.cm.hsv(hue))
    
    ax.scatter(theta, radius, c=colors, s=50, alpha=0.8)
    ax.set_ylim(0, 1.2)
    ax.set_title('Koło kolorów', y=1.08)
    ax.grid(True)
    
    # Konwertuj do base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()
    
    return base64.b64encode(image_png).decode('utf-8')


def analizuj_zdjecie_opencv(sciezka_obrazu):
    """Dodatkowa analiza używając OpenCV"""
    try:
        # Wczytaj obraz
        img = cv2.imread(sciezka_obrazu)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Zmień rozmiar dla szybszego przetwarzania
        img_small = cv2.resize(img, (150, 150))
        
        # Przekształć do jednowymiarowej tablicy pikseli
        pixels = img_small.reshape(-1, 3)
        
        # Usuń piksele bardzo ciemne lub bardzo jasne (szum)
        mask = np.all(pixels > 20, axis=1) & np.all(pixels < 235, axis=1)
        pixels_filtered = pixels[mask]
        
        if len(pixels_filtered) < 50:  # Za mało danych
            pixels_filtered = pixels
        
        # Klasteryzacja K-means dla dominujących kolorów
        n_colors = min(5, len(pixels_filtered))
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels_filtered)
        
        # Pobierz dominujące kolory
        dominant_colors = kmeans.cluster_centers_.astype(int)
        
        # Konwertuj na hex
        hex_colors = []
        for color in dominant_colors:
            hex_color = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
            hex_colors.append(hex_color)
        
        return hex_colors
        
    except Exception as e:
        print(f"Błąd analizy OpenCV: {e}")
        return ['#808080']  # Szary jako fallback


def porownaj_z_typami_kolorystycznymi(wyniki_analizy):
    """Porównuje wyniki analizy z bazą typów kolorystycznych"""
    from .models import TypKolorystyczny
    
    wszystkie_typy = TypKolorystyczny.objects.all()
    dopasowania = []
    
    for typ in wszystkie_typy:
        score = 0
        
        # Porównanie tonacji
        if typ.dominujaca_tonacja == wyniki_analizy['tonacja']:
            score += 3
        
        # Porównanie kontrastu
        typ_kontrast_map = {
            'niski': (1, 4),
            'średni': (4, 7), 
            'wysoki': (7, 10)
        }
        
        if typ.poziom_kontrastu in typ_kontrast_map:
            min_k, max_k = typ_kontrast_map[typ.poziom_kontrastu]
            if min_k <= wyniki_analizy['kontrast'] <= max_k:
                score += 2
        
        # Porównanie nasycenia
        typ_nasycenie_map = {
            'miękkie': (1, 4),
            'czyste': (4, 7),
            'głębokie': (7, 10)
        }
        
        if typ.nasycenie in typ_nasycenie_map:
            min_n, max_n = typ_nasycenie_map[typ.nasycenie]
            if min_n <= wyniki_analizy['nasycenie'] <= max_n:
                score += 2
        
        dopasowania.append({
            'typ': typ,
            'score': score,
            'pewnosc': min(1.0, score / 7.0)
        })
    
    # Sortuj według score
    dopasowania.sort(key=lambda x: x['score'], reverse=True)
    return dopasowania[:3]  # Top 3 dopasowania