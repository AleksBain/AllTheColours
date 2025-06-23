from django.shortcuts import render

# Create your views here.
import csv
import json
import os
from datetime import datetime
from io import BytesIO

import pandas as pd
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.contrib.auth.models import User
from django.http import HttpResponse

from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
import cv2
import colorsys
from collections import Counter

from .forms import (
    RejestracjaForm, AnalizaForm, FiltrAnalizForm, 
    EdycjaProfiluForm, PlikAnalizyForm, WybierTypForm
)
from .models import Analiza, TypKolorystyczny, ProfilUzytkownika, PlikAnalizy

# Import utility functions - create these if they don't exist
try:
    from .utils import analizuj_kolory, generuj_wykres_kolorow
except ImportError:
    # Fallback functions if utils don't exist
    def analizuj_kolory(kolory_skory, kolory_oczu, kolory_wlosow):
        """Fallback color analysis function"""
        # Simple analysis based on color brightness
        avg_brightness = sum([sum(color) for color in kolory_skory[:3]]) / (3 * 3)
        return {
            'tonacja': 'warm' if avg_brightness > 400 else 'cool',
            'kontrast': min(10, max(1, int(avg_brightness / 50))),
            'nasycenie': min(10, max(1, int(avg_brightness / 60))),
            'pewnosc': 0.7
        }
    
    def generuj_wykres_kolorow(analiza):
        """Fallback chart generation"""
        return {
            'kolory_skory': analiza.kolory_skory or [],
            'kolory_oczu': analiza.kolory_oczu or [],
            'kolory_wlosow': analiza.kolory_wlosow or []
        }

def preprocess_image(cv_image):
    """Preprocess image to improve color extraction"""
    try:
        # Convert to LAB color space for better color separation
        lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        lab[:,:,0] = clahe.apply(lab[:,:,0])
        
        # Convert back to BGR
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        return filtered
    except:
        return cv_image

def filter_extreme_pixels(pixels):
    """Remove pixels that are too dark or too bright"""
    try:
        # Convert to HSV to better filter based on brightness
        hsv_pixels = []
        for pixel in pixels:
            r, g, b = pixel / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            hsv_pixels.append([h, s, v])
        
        hsv_pixels = np.array(hsv_pixels)
        
        # Filter out very dark pixels (shadows) and very bright pixels (overexposure)
        # Also filter out very desaturated pixels (likely noise or lighting artifacts)
        mask = (
            (hsv_pixels[:, 2] > 0.15) &  # Value > 0.15 (not too dark)
            (hsv_pixels[:, 2] < 0.95) &  # Value < 0.95 (not too bright)
            (hsv_pixels[:, 1] > 0.1)     # Saturation > 0.1 (not too gray)
        )
        
        filtered_pixels = pixels[mask]
        return filtered_pixels if len(filtered_pixels) > 50 else pixels
    except:
        return pixels

def merge_similar_colors(weighted_colors, target_count):
    """Merge similar colors to get the final dominant colors"""
    if len(weighted_colors) <= target_count:
        return weighted_colors
    
    # Sort by weight
    sorted_colors = sorted(weighted_colors, key=lambda x: x[1], reverse=True)
    
    final_colors = []
    used_indices = set()
    
    for i, (color1, weight1) in enumerate(sorted_colors):
        if i in used_indices:
            continue
            
        # Start with current color
        merged_color = np.array(color1, dtype=float)
        total_weight = weight1
        used_indices.add(i)
        
        # Find similar colors to merge
        for j, (color2, weight2) in enumerate(sorted_colors[i+1:], i+1):
            if j in used_indices:
                continue
                
            # Calculate color distance
            distance = np.linalg.norm(np.array(color1) - np.array(color2))
            
            # If colors are similar (distance < threshold), merge them
            if distance < 50:  # Adjust threshold as needed
                merged_color = (merged_color * total_weight + np.array(color2) * weight2) / (total_weight + weight2)
                total_weight += weight2
                used_indices.add(j)
        
        final_colors.append((tuple(merged_color.astype(int)), total_weight))
        
        if len(final_colors) >= target_count:
            break
    
    return final_colors

def pobierz_dominujace_kolory(image_path, liczba_kolorow=5, crop_coords=None):
    """
    Improved dominant color extraction with preprocessing and filtering
    Now supports cropping to analyze only the relevant part of the image
    
    Args:
        image_path: Path to the image file
        liczba_kolorow: Number of dominant colors to extract
        crop_coords: Tuple (x, y, width, height) for cropping, or None for full image
    """
    try:
        # Load image using PIL
        image = Image.open(image_path).convert('RGB')
        
        # Apply crop if coordinates are provided
        if crop_coords:
            x, y, width, height = crop_coords
            # PIL crop uses (left, top, right, bottom) format
            image = image.crop((x, y, x + width, y + height))
        
        # Convert to OpenCV format for preprocessing
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Preprocessing steps
        cv_image = preprocess_image(cv_image)
        
        # Convert back to PIL format
        image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        
        # Resize for faster processing (but not too small)
        # Use larger size for better color representation
        image = image.resize((300, 300), Image.Resampling.LANCZOS)
        
        # Convert to numpy array
        pixels = np.array(image).reshape(-1, 3)
        
        # Remove very dark pixels (shadows) and very bright pixels (overexposure)
        pixels = filter_extreme_pixels(pixels)
        
        # Use more clusters initially, then merge similar colors
        initial_clusters = min(liczba_kolorow * 2, 10)
        kmeans = KMeans(n_clusters=initial_clusters, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get cluster centers and their labels
        colors = kmeans.cluster_centers_.astype(int)
        labels = kmeans.labels_
        
        # Count pixels in each cluster
        cluster_counts = Counter(labels)
        
        # Get colors with their weights
        weighted_colors = []
        for i, color in enumerate(colors):
            weight = cluster_counts[i] / len(pixels)
            weighted_colors.append((tuple(color), weight))
        
        # Sort by weight (most dominant first)
        weighted_colors.sort(key=lambda x: x[1], reverse=True)
        
        # Merge similar colors and select final colors
        final_colors = merge_similar_colors(weighted_colors, liczba_kolorow)
        
        # Convert to list of RGB tuples
        dominujace_kolory = [color for color, _ in final_colors]
        
        return dominujace_kolory
    
    except Exception as e:
        print(f"Error in pobierz_dominujace_kolory: {e}")
        # Return default colors in case of error
        return [(128, 128, 128)] * liczba_kolorow
        
  
def strona_glowna(request):
    """Home page with statistics"""
    try:
        analiza_count_by_typ = (
            Analiza.objects.filter(status='completed', typ_kolorystyczny__isnull=False)
            .values('typ_kolorystyczny__nazwa')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        typ_names = [item['typ_kolorystyczny__nazwa'] for item in analiza_count_by_typ]
        typ_counts = [item['count'] for item in analiza_count_by_typ]

        context = {
            'total_analiz': Analiza.objects.filter(status='completed').count(),
            'total_users': User.objects.count(),
            'total_types': TypKolorystyczny.objects.count(),
            'typy_kolorystyczne': TypKolorystyczny.objects.all()[:6],
            'ostatnie_analizy': Analiza.objects.filter(status='completed').order_by('-data_utworzenia')[:3],
            'typ_names_json': json.dumps(typ_names),
            'typ_counts_json': json.dumps(typ_counts),
        }
    except Exception as e:
        # Fallback context if database queries fail
        context = {
            'total_analiz': 0,
            'total_users': 0,
            'total_types': 0,
            'typy_kolorystyczne': [],
            'ostatnie_analizy': [],
            'typ_names_json': json.dumps([]),
            'typ_counts_json': json.dumps([]),
            'error_message': f'Database error: {str(e)}'
        }
    return render(request, 'color_analyzer/index.html', context)

def rejestracja(request):
    """User registration"""
    if request.method == 'POST':
        form = RejestracjaForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Account has been created!')
                return redirect('color_analyzer:strona_glowna')
            except Exception as e:
                messages.error(request, f'Error during account creation: {str(e)}')
    else:
        form = RejestracjaForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def nowa_analiza(request):
    """New color analysis form"""
    if request.method == 'POST':
        form = AnalizaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                analiza = form.save(commit=False)
                analiza.uzytkownik = request.user
                analiza.save()
                
                wykonaj_analize_kolorow(analiza)
                messages.success(request, 'Analysis has started!')
                return redirect('color_analyzer:szczegoly_analizy', pk=analiza.pk)
            except Exception as e:
                if 'analiza' in locals():
                    analiza.status = 'error'
                    analiza.save()
                messages.error(request, f'Error during analysis: {str(e)}')
    else:
        form = AnalizaForm()
    
    return render(request, 'color_analyzer/nowa_analiza.html', {'form': form})

def dopasuj_typ_kolorystyczny(wyniki):
    """
    Assigns color type based on analysis results: 
    wyniki = {'tonacja': 'warm' or 'cool', 'kontrast': 1-10, 'nasycenie': 1-10}
    """
    tonacja = (wyniki.get('tonacja') or '').strip().lower()
    kontrast = wyniki.get('kontrast', 0)
    nasycenie = wyniki.get('nasycenie', 0)

    # Set threshold values (can be adjusted in the future)
    kontrast_threshold = 7
    nasycenie_threshold = 7

    # Handle both English and Polish input for compatibility
    if tonacja in ['warm', 'ciepła', 'ciepla']:
        # Warm tones: Spring (high contrast) or Autumn (low contrast)
        if kontrast >= kontrast_threshold:
            # Spring subtypes
            if nasycenie >= nasycenie_threshold:
                return 'spring_clear'  # bright spring
            elif nasycenie <= (nasycenie_threshold - 4):
                return 'spring_light'
            else:
                return 'spring_warm'
        else:
            # Autumn subtypes
            if nasycenie >= nasycenie_threshold:
                return 'autumn_deep'
            elif nasycenie <= (nasycenie_threshold - 4):
                return 'autumn_soft'
            else:
                return 'autumn_warm'
    elif tonacja in ['cool', 'zimna']:
        # Cool tones: Winter (high contrast) or Summer (low contrast)
        if kontrast >= kontrast_threshold:
            # Winter subtypes
            if nasycenie >= nasycenie_threshold:
                return 'winter_clear'
            elif nasycenie <= (nasycenie_threshold - 4):
                return 'winter_deep'
            else:
                return 'winter_cool'
        else:
            # Summer subtypes
            if nasycenie >= nasycenie_threshold:
                return 'summer_light'
            elif nasycenie <= (nasycenie_threshold - 4):
                return 'summer_soft'
            else:
                return 'summer_cool'
    
    # Default if information is missing
    return 'undefined'

@login_required
def historia_analiz(request):
    """User's analysis history with filtering and pagination"""
    try:
        analizy = Analiza.objects.filter(uzytkownik=request.user)
        
        form = FiltrAnalizForm(request.GET)
        if form.is_valid():
            if form.cleaned_data.get('typ_kolorystyczny'):
                analizy = analizy.filter(typ_kolorystyczny=form.cleaned_data['typ_kolorystyczny'])
            if form.cleaned_data.get('data_od'):
                analizy = analizy.filter(data_utworzenia__date__gte=form.cleaned_data['data_od'])
            if form.cleaned_data.get('data_do'):
                analizy = analizy.filter(data_utworzenia__date__lte=form.cleaned_data['data_do'])
        
        if request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="analyses.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'Color Type', 'Status', 'Created At', 'Tone', 'Contrast', 'Saturation', 'Notes'])
            for analiza in analizy:
                writer.writerow([
                    analiza.pk,
                    analiza.typ_kolorystyczny.get_nazwa_display() if analiza.typ_kolorystyczny else '',
                    analiza.get_status_display(),
                    analiza.data_utworzenia.strftime('%Y-%m-%d %H:%M'),
                    analiza.tonacja_skory or '',
                    analiza.kontrast_poziom or '',
                    analiza.nasycenie_poziom or '',
                    analiza.notatki or '',
                ])
            return response 

        paginator = Paginator(analizy.order_by('-data_utworzenia'), 6)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'form': form,
            'total_count': analizy.count(),
        }
    except Exception as e:
        context = {
            'page_obj': None,
            'form': FiltrAnalizForm(),
            'total_count': 0,
            'error_message': f'Error: {str(e)}'
        }
    
    return render(request, 'color_analyzer/historia_analiz.html', context)

@login_required
def szczegoly_analizy(request, pk):
    """Analysis details"""
    try:
        analiza = get_object_or_404(Analiza, pk=pk, uzytkownik=request.user)
    except Http404:
        messages.error(request, 'Analysis not found.')
        return redirect('color_analyzer:historia_analiz')
    
    wybierz_typ_form = None
    if analiza.status == 'completed' and not analiza.typ_kolorystyczny:
        if request.method == 'POST':
            wybierz_typ_form = WybierTypForm(request.POST)
            if wybierz_typ_form.is_valid():
                try:
                    analiza.typ_kolorystyczny = wybierz_typ_form.cleaned_data['typ_kolorystyczny']
                    analiza.save()
                    messages.success(request, 'Color type has been saved!')
                    return redirect('color_analyzer:szczegoly_analizy', pk=pk)
                except Exception as e:
                    messages.error(request, f'Error while saving: {str(e)}')
        else:
            wybierz_typ_form = WybierTypForm()
    
    context = {
        'analiza': analiza,
        'wybierz_typ_form': wybierz_typ_form,
        'kolory_palette': analiza.typ_kolorystyczny.kolory_podstawowe if analiza.typ_kolorystyczny else []
    }
    return render(request, 'color_analyzer/szczegoly_analizy.html', context)

@login_required
def wykres_kolorow(request, pk):
    """Generates color chart for analysis"""
    try:
        analiza = get_object_or_404(Analiza, pk=pk, uzytkownik=request.user)
        
        if analiza.status != 'completed':
            return JsonResponse({'error': 'Analysis has not been completed'}, status=400)
        
        wykres_data = generuj_wykres_kolorow(analiza)
        return JsonResponse(wykres_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def profil_uzytkownika(request):
    """User profile"""
    try:
        profil, created = ProfilUzytkownika.objects.get_or_create(uzytkownik=request.user)
        
        if request.method == 'POST':
            form = EdycjaProfiluForm(request.POST, instance=profil)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile has been updated!')
                return redirect('color_analyzer:profil_uzytkownika')
        else:
            form = EdycjaProfiluForm(instance=profil)
        
        return render(request, 'color_analyzer/profil.html', {
            'form': form,
            'profil': profil
        })
    except Exception as e:
        messages.error(request, f'Error loading profile: {str(e)}')
        return redirect('color_analyzer:strona_glowna')

def typy_kolorystyczne(request):
    """List of all color types"""
    try:
        typy = TypKolorystyczny.objects.all().order_by('nazwa')
    except Exception as e:
        typy = []
        messages.error(request, f'Error loading color types: {str(e)}')
    
    return render(request, 'color_analyzer/typy_kolorystyczne.html', {'typy': typy})

def szczegoly_typu(request, pk):
    """Color type details"""
    try:
        typ = get_object_or_404(TypKolorystyczny, pk=pk)
        return render(request, 'color_analyzer/szczegoly_typu.html', {'typ': typ})
    except Http404:
        messages.error(request, 'Color type not found.')
        return redirect('color_analyzer:typy_kolorystyczne')

@login_required
def generuj_pdf_raport(request, pk):
    """Generates PDF report from analysis"""
    try:
        analiza = get_object_or_404(Analiza, pk=pk, uzytkownik=request.user)
        
        if analiza.status != 'completed':
            messages.error(request, 'Analysis has not been completed')
            return redirect('color_analyzer:szczegoly_analizy', pk=pk)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="analysis_{pk}.pdf"'
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # PDF content
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, "Color Analysis Report")
        p.setFont("Helvetica", 12)
        p.drawString(100, 730, f"Date: {analiza.data_utworzenia.strftime('%d.%m.%Y')}")
        
        if analiza.typ_kolorystyczny:
            p.drawString(100, 710, f"Type: {analiza.typ_kolorystyczny.get_nazwa_display()}")
            p.drawString(100, 690, f"Tone: {analiza.tonacja_skory or 'No data'}")
            p.drawString(100, 670, f"Contrast: {analiza.kontrast_poziom or 0}/10")
            p.drawString(100, 650, f"Saturation: {analiza.nasycenie_poziom or 0}/10")
        
        if analiza.notatki:
            p.drawString(100, 620, "Notes:")
            # Split long text
            lines = analiza.notatki.split('\n')
            y_pos = 600
            for line in lines:
                if len(line) > 80:
                    # Simple word wrap
                    words = line.split()
                    current_line = ""
                    for word in words:
                        if len(current_line + word) < 80:
                            current_line += word + " "
                        else:
                            p.drawString(100, y_pos, current_line)
                            y_pos -= 15
                            current_line = word + " "
                    if current_line:
                        p.drawString(100, y_pos, current_line)
                        y_pos -= 15
                else:
                    p.drawString(100, y_pos, line)
                    y_pos -= 15
        
        p.showPage()
        p.save()
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('color_analyzer:szczegoly_analizy', pk=pk)

def wykonaj_analize_kolorow(analiza):
    """Performs color analysis on uploaded photos"""
    try:
        analiza.status = 'processing'
        analiza.save()
        
        if not analiza.zdjecie_nadgarstka or not analiza.zdjecie_oczu or not analiza.zdjecie_wlosow:
            raise Exception("Required photos are missing")

        kolory_skory = pobierz_dominujace_kolory(analiza.zdjecie_nadgarstka.path)
        kolory_oczu = pobierz_dominujace_kolory(analiza.zdjecie_oczu.path)
        kolory_wlosow = pobierz_dominujace_kolory(analiza.zdjecie_wlosow.path)

        # Convert NumPy types to Python native types
        def convert_numpy_to_python(data):
            """Recursively convert NumPy types to Python native types"""
            import numpy as np
            
            if isinstance(data, (np.integer, np.int32, np.int64)):
                return int(data)
            elif isinstance(data, (np.floating, np.float32, np.float64)):
                return float(data)
            elif isinstance(data, np.ndarray):
                return data.tolist()
            elif isinstance(data, list):
                return [convert_numpy_to_python(item) for item in data]
            elif isinstance(data, tuple):
                return tuple(convert_numpy_to_python(item) for item in data)
            elif isinstance(data, dict):
                return {key: convert_numpy_to_python(value) for key, value in data.items()}
            else:
                return data

        # Convert all color data to Python native types
        analiza.kolory_skory = convert_numpy_to_python(kolory_skory)
        analiza.kolory_oczu = convert_numpy_to_python(kolory_oczu)
        analiza.kolory_wlosow = convert_numpy_to_python(kolory_wlosow)
        
        wyniki = analizuj_kolory(kolory_skory, kolory_oczu, kolory_wlosow)
        
        # Normalize tone and map to English values
        tonacja_raw = (wyniki.get('tonacja') or '').strip().lower()
        if tonacja_raw in ['ciepła', 'ciepla', 'warm']:
            analiza.tonacja_skory = 'warm'
        elif tonacja_raw in ['zimna', 'cool']:
            analiza.tonacja_skory = 'cool'
        else:
            analiza.tonacja_skory = tonacja_raw
        
        # Convert NumPy types for analysis results
        analiza.kontrast_poziom = convert_numpy_to_python(wyniki.get('kontrast', 0))
        analiza.nasycenie_poziom = convert_numpy_to_python(wyniki.get('nasycenie', 0))
        analiza.pewnosc_wyniku = convert_numpy_to_python(wyniki.get('pewnosc', 0.0))
        
        # Match color type
        typ_nazwa = dopasuj_typ_kolorystyczny(wyniki)
        
        if typ_nazwa and typ_nazwa != 'undefined':
            try:
                typ_obj = TypKolorystyczny.objects.get(nazwa=typ_nazwa)
                analiza.typ_kolorystyczny = typ_obj
            except TypKolorystyczny.DoesNotExist:
                analiza.notatki = (analiza.notatki or '') + f"\nWarning: Type '{typ_nazwa}' not found in database."
        else:
            analiza.notatki = (analiza.notatki or '') + "\nWarning: Could not automatically determine color type."
        
        analiza.status = 'completed'
        analiza.save()
        
    except Exception as e:
        analiza.status = 'error'
        analiza.notatki = f"Analysis error: {str(e)}"
        analiza.save()
        raise e