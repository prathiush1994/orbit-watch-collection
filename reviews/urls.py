from django.urls import path
from . import views

urlpatterns = [
    path('submit/<int:variant_id>/', views.submit_review, name='submit_review'),
    path('delete/<int:review_id>/', views.delete_review,  name='delete_review'),
]