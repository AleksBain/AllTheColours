from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = "color_analyzer"

urlpatterns = [
    
    path('', views.strona_glowna, name='strona_glowna'),
    
    
    path('rejestracja/', views.rejestracja, name='rejestracja'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    
   
    path('nowa-analiza/', views.nowa_analiza, name='nowa_analiza'),
    path('historia/', views.historia_analiz, name='historia_analiz'),
    path('analiza/<int:pk>/', views.szczegoly_analizy, name='szczegoly_analizy'),
    path('analiza/<int:pk>/wykres/', views.wykres_kolorow, name='wykres_kolorow'),
    
    
    
    path('eksport/csv/', views.eksport_csv, name='eksport_csv'),
    
    
    path('typy/', views.typy_kolorystyczne, name='typy_kolorystyczne'),
    path('typ/<int:pk>/', views.szczegoly_typu, name='szczegoly_typu'),
    
    
    path('profil/', views.profil_uzytkownika, name='profil_uzytkownika'),
    
    
    path('api/kontrast-slider/', views.api_kontrast_slider, name='api_kontrast_slider'),
]


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