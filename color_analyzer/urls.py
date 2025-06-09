from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = "color_analyzer"

urlpatterns = [
    # Strona główna
    path('', views.strona_glowna, name='strona_glowna'),
    
    # Autoryzacja
    path('rejestracja/', views.rejestracja, name='rejestracja'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    
    # Analizy
    path('nowa-analiza/', views.nowa_analiza, name='nowa_analiza'),
    path('historia/', views.historia_analiz, name='historia_analiz'),
    path('analiza/<int:pk>/', views.szczegoly_analizy, name='szczegoly_analizy'),
    path('analiza/<int:pk>/wykres/', views.wykres_kolorow, name='wykres_kolorow'),
    path('analiza/<int:pk>/plik/', views.przeslij_plik, name='przeslij_plik'),
    path('analiza/<int:pk>/pdf/', views.generuj_pdf_raport, name='generuj_pdf'),
    
    # Eksport danych
    path('eksport/csv/', views.eksport_csv, name='eksport_csv'),
    
    # Typy kolorystyczne
    path('typy/', views.typy_kolorystyczne, name='typy_kolorystyczne'),
    path('typ/<int:pk>/', views.szczegoly_typu, name='szczegoly_typu'),
    
    # Profil użytkownika
    path('profil/', views.profil_uzytkownika, name='profil_uzytkownika'),
    
    # API endpoints
    path('api/kontrast-slider/', views.api_kontrast_slider, name='api_kontrast_slider'),
]

# URLs głównego projektu (color_season/urls.py)
main_urls = """
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('color_analyzer.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
"""