from django.urls import path
from rest_framework.authtoken import views as drf_authtoken_views

app_name = 'accounts'

urlpatterns = [
    path('token/', drf_authtoken_views.obtain_auth_token, name='obtain-token'),
]
