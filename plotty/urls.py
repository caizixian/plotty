from django.conf.urls import url, include
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    url(r'^', include('results.urls')),
]
