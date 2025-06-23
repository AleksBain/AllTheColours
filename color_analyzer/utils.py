# utils.py - Emergency fallback functions
import colorsys
from PIL import Image
import numpy as np



def pobierz_dominujace_kolory(image_path, num_colors=5):
    """Extract dominant colors from image"""
    try:
        # Open and resize image for faster processing
        image = Image.open(image_path)
        image = image.convert('RGB')
        image = image.resize((150, 150))

        # Get pixel data
        pixels = np.array(image)
        pixels = pixels.reshape(-1, 3)

        # Simple clustering - get most common colors
        from collections import Counter

        # Reduce color space to make clustering more effective
        pixels = (pixels // 32) * 32

        # Count color frequencies
        color_counts = Counter(map(tuple, pixels))

        # Get top colors and convert to int to avoid uint8 serialization issues
        dominant_colors = [
            tuple(int(x) for x in color)
            for color, _ in color_counts.most_common(num_colors)
        ]

        return dominant_colors
    except Exception as e:
        print(f"Error extracting colors: {e}")
        # Return default colors if extraction fails
        return [(200, 150, 120), (180, 140, 110), (160, 130, 100), (140, 120, 90), (120, 110, 80)]


def analizuj_kolory(kolory_skory, kolory_oczu, kolory_wlosow):
    """Analyze colors and determine skin tone characteristics"""
    try:
        # Convert to HSV for better analysis
        def rgb_to_hsv(rgb):
            r, g, b = [x/255.0 for x in rgb]
            return colorsys.rgb_to_hsv(r, g, b)
        
        # Analyze skin tone
        skin_hsv = [rgb_to_hsv(color) for color in kolory_skory[:3]]
        
        # Calculate average hue
        avg_hue = sum(hsv[0] for hsv in skin_hsv) / len(skin_hsv)
        avg_saturation = sum(hsv[1] for hsv in skin_hsv) / len(skin_hsv)
        avg_value = sum(hsv[2] for hsv in skin_hsv) / len(skin_hsv)
        
        # Determine warm/cool based on hue
        # Red/orange/yellow hues (0-0.17, 0.83-1.0) are warm
        # Blue/green hues (0.17-0.83) are cool
        if avg_hue < 0.17 or avg_hue > 0.83:
            tonacja = 'warm'
        else:
            tonacja = 'cool'
        
        # Calculate contrast (based on value range)
        values = [hsv[2] for hsv in skin_hsv]
        contrast_range = max(values) - min(values)
        kontrast = min(10, max(1, int(contrast_range * 50)))
        
        # Calculate saturation level
        nasycenie = min(10, max(1, int(avg_saturation * 10)))
        
        # Confidence based on color consistency
        pewnosc = 1.0 - contrast_range
        
        return {
            'tonacja': tonacja,
            'kontrast': kontrast,
            'nasycenie': nasycenie,
            'pewnosc': pewnosc
        }
    except Exception as e:
        print(f"Error analyzing colors: {e}")
        # Return default analysis
        return {
            'tonacja': 'warm',
            'kontrast': 5,
            'nasycenie': 5,
            'pewnosc': 0.5
        }

def generuj_wykres_kolorow(analiza):
    """Zwraca dane do wykresu dominujących kolorów: skóra, oczy, włosy."""
    try:
        def kolor_hex(kolor):
            if isinstance(kolor, (list, tuple)) and len(kolor) >= 3:
                r, g, b = kolor[:3]
                return f'#{r:02x}{g:02x}{b:02x}'
            return '#cccccc'

        kolory = {
            'Skin': analiza.kolory_skory,
            'Eyes': analiza.kolory_oczu,
            'Hair': analiza.kolory_wlosow,
        }

        labels = []
        values = []
        colors = []

        for label, color_list in kolory.items():
            labels.append(label)
            values.append(1)  # Równy udział każdej cechy w wykresie
            if color_list and len(color_list) > 0:
                colors.append(kolor_hex(color_list[0]))  # pierwszy dominujący kolor
            else:
                colors.append('#cccccc')  # szary jako brak danych

        return {
            'labels': labels,
            'values': values,
            'colors': colors
        }

    except Exception as e:
        print(f"Błąd przy generowaniu wykresu: {e}")
        return {
            'labels': ['Skin', 'Eyes', 'Hair'],
            'values': [1, 1, 1],
            'colors': ['#dddddd', '#bbbbbb', '#999999'],
            'error': str(e)
        }
