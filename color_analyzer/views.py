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
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.contrib.auth.models import User
from django.http import HttpResponse

from .forms import (
    RejestracjaForm, AnalizaForm, FiltrAnalizForm, 
    EdycjaProfiluForm, PlikAnalizyForm, WybierTypForm
)
from .models import Analiza, TypKolorystyczny, ProfilUzytkownika, PlikAnalizy
from .utils import analizuj_kolory, generuj_wykres_kolorow, pobierz_dominujace_kolory


def strona_glowna(request):
    """Strona główna aplikacji"""
    
    context = {
        'total_analiz': Analiza.objects.filter(status='completed').count(),
        'total_users': User.objects.count(),
        'total_types': TypKolorystyczny.objects.count(),
        'typy_kolorystyczne': TypKolorystyczny.objects.all()[:6],
        'ostatnie_analizy': Analiza.objects.filter(status='completed').order_by('-data_utworzenia')[:3]
    }
    return render(request, 'color_analyzer/index.html', context)


def rejestracja(request):
    """Rejestracja nowego użytkownika"""
    if request.method == 'POST':
        form = RejestracjaForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Konto zostało utworzone!')
            return redirect('color_analyzer:strona_glowna')
    else:
        form = RejestracjaForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def nowa_analiza(request):
    """Formularz nowej analizy kolorystycznej"""
    if request.method == 'POST':
        form = AnalizaForm(request.POST, request.FILES)
        if form.is_valid():
            analiza = form.save(commit=False)
            analiza.uzytkownik = request.user
            analiza.save()
            
            # Rozpocznij analizę kolorów
            try:
                wykonaj_analize_kolorow(analiza)
                messages.success(request, 'Analiza została rozpoczęta!')
                return redirect('color_analyzer:szczegoly_analizy', pk=analiza.pk)
            except Exception as e:
                analiza.status = 'error'
                analiza.save()
                messages.error(request, f'Błąd podczas analizy: {str(e)}')
    else:
        form = AnalizaForm()
    
    return render(request, 'color_analyzer/nowa_analiza.html', {'form': form})


@login_required
def historia_analiz(request):
    """Lista analiz użytkownika z filtrowaniem i stronicowaniem"""
    analizy = Analiza.objects.filter(uzytkownik=request.user)
    
    # Filtrowanie
    form = FiltrAnalizForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('typ_kolorystyczny'):
            analizy = analizy.filter(typ_kolorystyczny=form.cleaned_data['typ_kolorystyczny'])
        if form.cleaned_data.get('data_od'):
            analizy = analizy.filter(data_utworzenia__date__gte=form.cleaned_data['data_od'])
        if form.cleaned_data.get('data_do'):
            analizy = analizy.filter(data_utworzenia__date__lte=form.cleaned_data['data_do'])
    
    # Eksport do CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="analizy.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Typ kolorystyczny', 'Status', 'Data utworzenia', 'Tonacja', 'Kontrast', 'Nasycenie', 'Notatki'])
        for analiza in analizy:
            writer.writerow([
                analiza.pk,
                analiza.typ_kolorystyczny.get_nazwa_display() if analiza.typ_kolorystyczny else '',
                analiza.get_status_display(),
                analiza.data_utworzenia.strftime('%Y-%m-%d %H:%M'),
                analiza.tonacja_skory,
                analiza.kontrast_poziom,
                analiza.nasycenie_poziom,
                analiza.notatki,
            ])
        return response  # <-- Zwracamy response od razu!

    # Stronicowanie
    paginator = Paginator(analizy, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'total_count': analizy.count(),
    }
    return render(request, 'color_analyzer/historia_analiz.html', context)


@login_required
def szczegoly_analizy(request, pk):
    """Szczegóły konkretnej analizy"""
    analiza = get_object_or_404(Analiza, pk=pk, uzytkownik=request.user)
    
    # Jeśli analiza nie ma przypisanego typu i jest gotowa, pokaż opcje wyboru
    wybierz_typ_form = None
    if analiza.status == 'completed' and not analiza.typ_kolorystyczny:
        if request.method == 'POST':
            wybierz_typ_form = WybierTypForm(request.POST)
            if wybierz_typ_form.is_valid():
                analiza.typ_kolorystyczny = wybierz_typ_form.cleaned_data['typ_kolorystyczny']
                analiza.save()
                messages.success(request, 'Typ kolorystyczny został zapisany!')
                return redirect('color_analyzer:szczegoly_analizy', pk=pk)
        else:
            wybierz_typ_form = WybierTypForm()
    
    context = {
        'analiza': analiza,
        'wybierz_typ_form': wybierz_typ_form,
        'kolory_palette': analiza.typ_kolorystyczny.kolory_podstawowe if analiza.typ_kolorystyczny else []
    }
    return render(request, 'color_analyzer/szczegoly_analizy.html', context)


@login_required
def eksport_csv(request):
    """Eksport danych analiz do CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="analizy.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Data', 'Status', 'Typ kolorystyczny', 'Tonacja skóry', 
        'Kontrast', 'Nasycenie', 'Pewność wyniku'
    ])
    
    analizy = Analiza.objects.filter(uzytkownik=request.user).order_by('-data_utworzenia')
    for analiza in analizy:
        writer.writerow([
            analiza.data_utworzenia.strftime('%Y-%m-%d %H:%M'),
            analiza.get_status_display(),
            analiza.typ_kolorystyczny.get_nazwa_display() if analiza.typ_kolorystyczny else '',
            analiza.tonacja_skory or '',
            analiza.kontrast_poziom or '',
            analiza.nasycenie_poziom or '',
            f"{analiza.pewnosc_wyniku:.2f}" if analiza.pewnosc_wyniku else ''
        ])
    
    return response


@login_required
def wykres_kolorow(request, pk):
    """Generuje wykres kolorów dla analizy"""
    analiza = get_object_or_404(Analiza, pk=pk, uzytkownik=request.user)
    
    if analiza.status != 'completed':
        return JsonResponse({'error': 'Analiza nie została ukończona'}, status=400)
    
    try:
        wykres_data = generuj_wykres_kolorow(analiza)
        return JsonResponse(wykres_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def przeslij_plik(request, pk):
    """Przesyłanie dodatkowych plików do analizy"""
    analiza = get_object_or_404(Analiza, pk=pk, uzytkownik=request.user)
    
    if request.method == 'POST':
        form = PlikAnalizyForm(request.POST, request.FILES)
        if form.is_valid():
            plik_obj = form.save(commit=False)
            plik_obj.analiza = analiza
            plik_obj.nazwa_pliku = plik_obj.plik.name
            plik_obj.rozmiar = plik_obj.plik.size
            plik_obj.save()
            
            # Przetwórz plik jeśli to CSV/XLSX
            if plik_obj.plik.name.endswith(('.csv', '.xlsx')):
                try:
                    przetwarz_plik_danych(plik_obj)
                    messages.success(request, 'Plik został przesłany i przetworzony!')
                except Exception as e:
                    messages.warning(request, f'Plik przesłano, ale wystąpił błąd: {str(e)}')
            else:
                messages.success(request, 'Plik został przesłany!')
            
            return redirect('color_analyzer:szczegoly_analizy', pk=pk)
    else:
        form = PlikAnalizyForm()
    
    return render(request, 'color_analyzer/przeslij_plik.html', {
        'form': form,
        'analiza': analiza
    })


@login_required
def profil_uzytkownika(request):
    """Profil użytkownika"""
    profil, created = ProfilUzytkownika.objects.get_or_create(uzytkownik=request.user)
    
    if request.method == 'POST':
        form = EdycjaProfiluForm(request.POST, instance=profil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil został zaktualizowany!')
            return redirect('color_analyzer:profil_uzytkownika')
    else:
        form = EdycjaProfiluForm(instance=profil)
    
    return render(request, 'color_analyzer/profil.html', {
        'form': form,
        'profil': profil
    })


def typy_kolorystyczne(request):
    """Lista wszystkich typów kolorystycznych"""
    typy = TypKolorystyczny.objects.all().order_by('nazwa')
    return render(request, 'color_analyzer/typy_kolorystyczne.html', {'typy': typy})


def szczegoly_typu(request, pk):
    """Szczegóły typu kolorystycznego"""
    typ = get_object_or_404(TypKolorystyczny, pk=pk)
    return render(request, 'color_analyzer/szczegoly_typu.html', {'typ': typ})


@login_required
def generuj_pdf_raport(request, pk):
    """Generuje raport PDF z analizy"""
    analiza = get_object_or_404(Analiza, pk=pk, uzytkownik=request.user)
    
    if analiza.status != 'completed':
        messages.error(request, 'Analiza nie została ukończona')
        return redirect('color_analyzer:szczegoly_analizy', pk=pk)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="analiza_{pk}.pdf"'
    
    # Generuj PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Nagłówek
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"Raport Analizy Kolorystycznej")
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"Data: {analiza.data_utworzenia.strftime('%d.%m.%Y')}")
    
    if analiza.typ_kolorystyczny:
        p.drawString(100, 710, f"Typ: {analiza.typ_kolorystyczny.get_nazwa_display()}")
        p.drawString(100, 690, f"Tonacja: {analiza.tonacja_skory}")
        p.drawString(100, 670, f"Kontrast: {analiza.kontrast_poziom}/10")
        p.drawString(100, 650, f"Nasycenie: {analiza.nasycenie_poziom}/10")
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


def wykonaj_analize_kolorow(analiza):
    """Wykonuje analizę kolorów na przesłanych zdjęciach"""
    try:
        analiza.status = 'processing'
        analiza.save()
        
        # Analiza kolorów z każdego zdjęcia
        kolory_skory = pobierz_dominujace_kolory(analiza.zdjecie_nadgarstka.path)
        kolory_oczu = pobierz_dominujace_kolory(analiza.zdjecie_oczu.path)
        kolory_wlosow = pobierz_dominujace_kolory(analiza.zdjecie_wlosow.path)
        
        analiza.kolory_skory = kolory_skory
        analiza.kolory_oczu = kolory_oczu
        analiza.kolory_wlosow = kolory_wlosow
        
        # Określenie tonacji i kontrastów
        wyniki = analizuj_kolory(kolory_skory, kolory_oczu, kolory_wlosow)
        analiza.tonacja_skory = wyniki['tonacja']
        analiza.kontrast_poziom = wyniki['kontrast']
        analiza.nasycenie_poziom = wyniki['nasycenie']
        analiza.pewnosc_wyniku = wyniki['pewnosc']
        
        # Przypisanie typu kolorystycznego
        typ = dopasuj_typ_kolorystyczny(wyniki)
        if typ:
            analiza.typ_kolorystyczny = typ
        
        analiza.status = 'completed'
        analiza.save()
        
    except Exception as e:
        analiza.status = 'error'
        analiza.notatki = f"Błąd analizy: {str(e)}"
        analiza.save()
        raise e


def dopasuj_typ_kolorystyczny(wyniki):
    """Dopasowuje typ kolorystyczny na podstawie wyników analizy"""
    tonacja = wyniki['tonacja']
    kontrast = wyniki['kontrast']
    nasycenie = wyniki['nasycenie']
    
    # Logika dopasowania typu na podstawie parametrów
    if tonacja == 'ciepła':
        if kontrast <= 4:
            if nasycenie <= 4:
                return TypKolorystyczny.objects.filter(nazwa='autumn_soft').first()
            else:
                return TypKolorystyczny.objects.filter(nazwa='spring_warm').first()
        else:
            if nasycenie <= 6:
                return TypKolorystyczny.objects.filter(nazwa='autumn_warm').first()
            else:
                return TypKolorystyczny.objects.filter(nazwa='autumn_deep').first()
    else:  # zimna
        if kontrast <= 4:
            if nasycenie <= 4:
                return TypKolorystyczny.objects.filter(nazwa='summer_soft').first()
            else:
                return TypKolorystyczny.objects.filter(nazwa='summer_light').first()
        else:
            if nasycenie <= 6:
                return TypKolorystyczny.objects.filter(nazwa='winter_cool').first()
            else:
                return TypKolorystyczny.objects.filter(nazwa='winter_deep').first()


def przetwarz_plik_danych(plik_obj):
    """Przetwarzanie przesłanych plików CSV/XLSX"""
    try:
        if plik_obj.plik.name.endswith('.csv'):
            df = pd.read_csv(plik_obj.plik.path)
        elif plik_obj.plik.name.endswith('.xlsx'):
            df = pd.read_excel(plik_obj.plik.path)
        else:
            return
        
        # Przykładowe przetwarzanie - można rozszerzyć
        if 'tonacja' in df.columns:
            plik_obj.analiza.notatki += f"\nDane z pliku: {df['tonacja'].value_counts().to_dict()}"
            plik_obj.analiza.save()
            
    except Exception as e:
        raise Exception(f"Błąd przetwarzania pliku: {str(e)}")


# API endpoints dla AJAX
@csrf_exempt
def api_kontrast_slider(request):
    """API endpoint dla slidera kontrastu"""
    if request.method == 'POST':
        data = json.loads(request.body)
        kontrast_value = data.get('kontrast', 5)
        
        # Zwróć sugerowane typy na podstawie kontrastu
        if kontrast_value <= 3:
            typy = TypKolorystyczny.objects.filter(
                nazwa__in=['summer_soft', 'autumn_soft']
            )
        elif kontrast_value <= 7:
            typy = TypKolorystyczny.objects.filter(
                nazwa__in=['summer_cool', 'autumn_warm', 'spring_warm']
            )
        else:
            typy = TypKolorystyczny.objects.filter(
                nazwa__in=['winter_deep', 'winter_clear', 'autumn_deep']
            )
        
        return JsonResponse({
            'typy': [{'id': t.id, 'nazwa': t.get_nazwa_display()} for t in typy]
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


#################################

# Add this debug view to your views.py to check what types exist in your database

@login_required
def debug_typy_kolorystyczne(request):
    """Debug view to check existing color types"""
    typy = TypKolorystyczny.objects.all()
    debug_info = []
    
    for typ in typy:
        debug_info.append({
            'id': typ.id,
            'nazwa': typ.nazwa,
            'get_nazwa_display': typ.get_nazwa_display() if hasattr(typ, 'get_nazwa_display') else 'No display method',
            'all_fields': {field.name: getattr(typ, field.name) for field in typ._meta.fields}
        })
    
    return JsonResponse({
        'total_types': typy.count(),
        'types': debug_info
    }, indent=2)


# Fixed dopasuj_typ_kolorystyczny function based on your SEZONY choices
def dopasuj_typ_kolorystyczny(wyniki):
    """Dopasowuje typ kolorystyczny na podstawie wyników analizy"""
    tonacja = wyniki['tonacja']
    kontrast = wyniki['kontrast']
    nasycenie = wyniki['nasycenie']
    
    # First, let's see what types are available
    wszystkie_typy = TypKolorystyczny.objects.all()
    
    # Debug: log available types
    print(f"Available types: {[typ.nazwa for typ in wszystkie_typy]}")
    print(f"Analysis results - Tonacja: {tonacja}, Kontrast: {kontrast}, Nasycenie: {nasycenie}")
    
    # If no types exist, return None
    if not wszystkie_typy.exists():
        print("No color types found in database!")
        return None
    
    # Use the exact SEZONY values from your model
    # Based on your SEZONY choices, here's the mapping:
    if tonacja == 'ciepła':
        if kontrast <= 4:
            if nasycenie <= 4:
                # Soft, low contrast warm = Miękka Jesień
                typ = wszystkie_typy.filter(nazwa='autumn_soft').first()
            else:
                # High saturation, low contrast warm = Jasna Wiosna
                typ = wszystkie_typy.filter(nazwa='spring_light').first()
        else:  # high contrast
            if nasycenie <= 6:
                # Medium saturation, high contrast warm = Ciepła Jesień
                typ = wszystkie_typy.filter(nazwa='autumn_warm').first()
            else:
                # High saturation, high contrast warm = Głęboka Jesień or Ciepła Wiosna
                typ = wszystkie_typy.filter(nazwa='autumn_deep').first()
                if not typ:
                    typ = wszystkie_typy.filter(nazwa='spring_warm').first()
    else:  # zimna tonacja
        if kontrast <= 4:
            if nasycenie <= 4:
                # Soft, low contrast cool = Miękkie Lato
                typ = wszystkie_typy.filter(nazwa='summer_soft').first()
            else:
                # High saturation, low contrast cool = Jasne Lato
                typ = wszystkie_typy.filter(nazwa='summer_light').first()
        else:  # high contrast
            if nasycenie <= 6:
                # Medium saturation, high contrast cool = Chłodne Lato or Chłodna Zima
                typ = wszystkie_typy.filter(nazwa='summer_cool').first()
                if not typ:
                    typ = wszystkie_typy.filter(nazwa='winter_cool').first()
            else:
                # High saturation, high contrast cool = Głęboka Zima or Czysta Zima
                typ = wszystkie_typy.filter(nazwa='winter_deep').first()
                if not typ:
                    typ = wszystkie_typy.filter(nazwa='winter_clear').first()
    
    if typ:
        print(f"Found matching type: {typ.nazwa} - {typ.get_nazwa_display()}")
        return typ
    
    # Fallback 1: Try any warm/cool season
    if tonacja == 'ciepła':
        # Try any spring or autumn type
        for season_type in ['spring_light', 'spring_warm', 'spring_clear', 'autumn_soft', 'autumn_warm', 'autumn_deep']:
            typ = wszystkie_typy.filter(nazwa=season_type).first()
            if typ:
                print(f"Found warm season fallback: {typ.nazwa}")
                return typ
    else:  # zimna
        # Try any summer or winter type
        for season_type in ['summer_light', 'summer_cool', 'summer_soft', 'winter_cool', 'winter_clear', 'winter_deep']:
            typ = wszystkie_typy.filter(nazwa=season_type).first()
            if typ:
                print(f"Found cool season fallback: {typ.nazwa}")
                return typ
    
    # Fallback 2: Return first available type
    pierwszy_typ = wszystkie_typy.first()
    if pierwszy_typ:
        print(f"Using first available type as fallback: {pierwszy_typ.nazwa}")
        return pierwszy_typ
    
    print("No suitable type found!")
    return None


# Alternative approach - let user choose the type manually
def wykonaj_analize_kolorow(analiza):
    """Wykonuje analizę kolorów na przesłanych zdjęciach"""
    try:
        analiza.status = 'processing'
        analiza.save()
        
        # Analiza kolorów z każdego zdjęcia
        kolory_skory = pobierz_dominujace_kolory(analiza.zdjecie_nadgarstka.path)
        kolory_oczu = pobierz_dominujace_kolory(analiza.zdjecie_oczu.path)
        kolory_wlosow = pobierz_dominujace_kolory(analiza.zdjecie_wlosow.path)
        
        analiza.kolory_skory = kolory_skory
        analiza.kolory_oczu = kolory_oczu
        analiza.kolory_wlosow = kolory_wlosow
        
        # Określenie tonacji i kontrastów
        wyniki = analizuj_kolory(kolory_skory, kolory_oczu, kolory_wlosow)
        analiza.tonacja_skory = wyniki['tonacja']
        analiza.kontrast_poziom = wyniki['kontrast']
        analiza.nasycenie_poziom = wyniki['nasycenie']
        analiza.pewnosc_wyniku = wyniki['pewnosc']
        
        # Przypisanie typu kolorystycznego - improved version
        typ = dopasuj_typ_kolorystyczny(wyniki)
        if typ:
            analiza.typ_kolorystyczny = typ
            print(f"Assigned type: {typ.nazwa}")
        else:
            print("No type assigned - user will need to choose manually")
            # Add a note for manual selection
            analiza.notatki = (analiza.notatki or "") + "\nTyp kolorystyczny wymaga ręcznego wyboru."
        
        analiza.status = 'completed'
        analiza.save()
        
        print(f"Analysis completed for {analiza.id}")
        
    except Exception as e:
        analiza.status = 'error'
        analiza.notatki = f"Błąd analizy: {str(e)}"
        analiza.save()
        print(f"Analysis failed for {analiza.id}: {str(e)}")
        raise e


# Add this to check what's in your database
def check_database_types():
    """Helper function to check what's actually in your database"""
    typy = TypKolorystyczny.objects.all()
    print("=== DATABASE TYPES ===")
    for typ in typy:
        print(f"ID: {typ.id}, Nazwa: {typ.nazwa}")
        try:
            print(f"  Display: {typ.get_nazwa_display()}")
        except:
            print(f"  No get_nazwa_display method")
        print("---")
    print(f"Total types: {typy.count()}")
    return typy