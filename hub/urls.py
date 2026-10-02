from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('read/<slug:slug>/', views.entry_detail, name='entry'),
    path('download/<slug:slug>/', views.download, name='download'),
    path('search/', views.search, name='search'),
    path('editor/', views.editor, name='editor'),
    path('healthz/', views.health, name='health'),
    path('robots.txt', views.robots),
    path('<slug:section>/', views.listing, name='listing'),
]
