from django.urls import path
from . import views

app_name = 'onlinecourse'

urlpatterns = [
    path('', views.course_list, name='index'),
    path('registration/', views.registration_request, name='registration'),
    path('login/', views.login_request, name='login'),
    path('logout/', views.logout_request, name='logout'),
    path('course/<int:course_id>/', views.course_details, name='course_details'),
    path('course/<int:course_id>/enroll/', views.enroll, name='enroll'),
]