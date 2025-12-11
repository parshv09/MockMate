from django.urls import path
from . import views

app_name = 'interviewapp'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('start/', views.start_session, name='start_session'),
    path('session/<int:session_id>/next/', views.next_question, name='next_question'),
    path('session/<int:session_id>/submit/', views.submit_answer, name='submit_answer'),
    path('session/<int:session_id>/skip/', views.skip_question, name='skip_question'),  # NEW
    path('session/<int:session_id>/end/', views.end_session, name='end_session'),      # NEW
    path('session/<int:session_id>/summary/', views.session_summary, name='session_summary'),
    path('start-simple/', views.start_session_simple, name='start_session_simple'),
]