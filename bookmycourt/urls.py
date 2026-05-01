"""
URL configuration for bookmycourt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from pickleball import views
from django.shortcuts import redirect

urlpatterns = [
    path('',lambda request: redirect('home')),
    path('admin/', admin.site.urls),
    path(' ',include('pickleball.urls')),
    path('home/', views.home, name='home'),
    path('register/',views.register,name='Register'),
    path('login/',views.login,name='Login'),
    path('booking/',views.book_pg,name='book_pg'),
    path('courts/<str:game_type>/',views.court_list,name='court_list'),
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("toggle_court/<int:court_id>/", views.toggle_court, name="toggle_court"),
    path('set_cookie/', views.set_cookie_view, name='set_cookie'),
    path('get_cookie/', views.get_cookie_view, name='get_cookie'),
]

