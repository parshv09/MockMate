"""
URL configuration for MockMate REST API v1.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views.auth_views import (
    LoginAPIView,
    MeAPIView,
    RegisterAPIView,
)
from .views.resume_views import (
    ResumeDetailAPIView,
    ResumeListCreateAPIView,
)
from .views.session_views import (
    SessionAnswerSubmitAPIView,
    SessionDetailAPIView,
    SessionEndAPIView,
    SessionListCreateAPIView,
    SessionNextQuestionAPIView,
    SessionQuestionSkipAPIView,
    SessionReportDownloadAPIView,
    SessionResumeJDCreateAPIView,
    SessionSummaryAPIView,
)
from .views.video_views import (
    SessionAvatarTokenAPIView,
    SessionVideoFinalizeAPIView,
    SessionVideoFrameAPIView,
    SessionVideoMetricsAPIView,
)

app_name = "api_v1"

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", RegisterAPIView.as_view(), name="auth_register"),
    path("auth/login/", LoginAPIView.as_view(), name="auth_login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("auth/me/", MeAPIView.as_view(), name="auth_me"),

    # Resume management endpoints
    path("resumes/", ResumeListCreateAPIView.as_view(), name="resume_list_create"),
    path("resumes/<int:pk>/", ResumeDetailAPIView.as_view(), name="resume_detail"),

    # Interview session endpoints
    path("sessions/", SessionListCreateAPIView.as_view(), name="session_list_create"),
    path("sessions/resume-jd/", SessionResumeJDCreateAPIView.as_view(), name="session_resume_jd_create"),
    path("sessions/<int:pk>/", SessionDetailAPIView.as_view(), name="session_detail"),
    path("sessions/<int:pk>/next-question/", SessionNextQuestionAPIView.as_view(), name="session_next_question"),
    path("sessions/<int:pk>/answers/", SessionAnswerSubmitAPIView.as_view(), name="session_answer_submit"),
    path("sessions/<int:pk>/skip/", SessionQuestionSkipAPIView.as_view(), name="session_question_skip"),
    path("sessions/<int:pk>/end/", SessionEndAPIView.as_view(), name="session_end"),
    path("sessions/<int:pk>/summary/", SessionSummaryAPIView.as_view(), name="session_summary"),
    path("sessions/<int:pk>/report/", SessionReportDownloadAPIView.as_view(), name="session_report_download"),
    path("sessions/<int:pk>/video/frame/", SessionVideoFrameAPIView.as_view(), name="session_video_frame"),
    path("sessions/<int:pk>/video/metrics/", SessionVideoMetricsAPIView.as_view(), name="session_video_metrics"),
    path("sessions/<int:pk>/video/finalize/", SessionVideoFinalizeAPIView.as_view(), name="session_video_finalize"),
    path("sessions/<int:pk>/avatar/token/", SessionAvatarTokenAPIView.as_view(), name="session_avatar_token"),
]

