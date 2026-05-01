from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('booking/', views.book_pg, name='booking'),

    # Show all courts by game type
    #path('pickleball_court/<str:game_type>/', views.court_list, name='court_list'),
    path('book-court/<str:game_type>/', views.court_list, name='court_list'),

    # Book specific court by ID
    path('book/<int:court_id>/', views.book_court, name='book_court'),

    #path('confirm/', views.confirm_booking, name='confirm_booking'),
    path('payment/', views.payment, name='payment'),
    path('success/', views.success, name='success'),
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path('payment-status/<int:booking_id>/', views.payment_status, name='payment_status'),
    path("toggle_court/<int:court_id>/", views.toggle_court, name="toggle_court"),
    path('set_cookie/', views.set_cookie_view, name='set_cookie'),
    path('get_cookie/', views.get_cookie_view, name='get_cookie'),

]



