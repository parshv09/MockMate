# interviewapp/views.py
import logging
from collections import defaultdict
from io import BytesIO

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AnswerForm, StartSessionForm
from .models import Answer, GeneratedQuestion, InterviewSession, Resume, SessionQuestion, UserProfile
from .qgen_groq import generate_ai_roadmap
from .services import (
    ROLE_MAP,
    SESSION_VIDEO_STATS,
    AnswerClaimError,
    AnswerDatabaseContentionError,
    build_session_pdf_report,
    create_phase_practice_session,
    create_resume_jd_session,
    create_standard_session,
    end_candidate_session,
    extract_text_from_resume_file,
    get_next_unprocessed_answer,
    get_session_summary_data,
    process_video_frame,
    save_and_index_resume,
    skip_candidate_question,
    submit_candidate_answer,
    validate_resume_file,
)

logger = logging.getLogger(__name__)


def home_page(request):
    return render(request, "home.html")


def register(request):
    """
    Handle user registration with proper validation and profile creation.
    """
    if request.user.is_authenticated:
        return redirect("interviewapp:dashboard")

    if request.method == "POST":
        form_data = {
            "first_name": request.POST.get("first_name", "").strip(),
            "last_name": request.POST.get("last_name", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "username": request.POST.get("username", "").strip(),
            "password": request.POST.get("password", "").strip(),
            "confirm_password": request.POST.get("confirm_password", "").strip(),
            "user_type": request.POST.get("user_type", "student"),
            "target_role": request.POST.get("target_role", ""),
        }

        errors = {}

        if not form_data["first_name"]:
            errors["first_name"] = "First name is required."

        if not form_data["last_name"]:
            errors["last_name"] = "Last name is required."

        if not form_data["email"]:
            errors["email"] = "Email address is required."
        elif "@" not in form_data["email"]:
            errors["email"] = "Please enter a valid email address."
        elif User.objects.filter(email=form_data["email"]).exists():
            errors["email"] = "This email is already registered."

        if not form_data["username"]:
            errors["username"] = "Username is required."
        elif len(form_data["username"]) < 3:
            errors["username"] = "Username must be at least 3 characters."
        elif User.objects.filter(username=form_data["username"]).exists():
            errors["username"] = "This username is already taken."

        if not form_data["password"]:
            errors["password"] = "Password is required."
        elif len(form_data["password"]) < 8:
            errors["password"] = "Password must be at least 8 characters."
        elif not any(c.isupper() for c in form_data["password"]):
            errors["password"] = "Password must contain at least one uppercase letter."
        elif not any(c.islower() for c in form_data["password"]):
            errors["password"] = "Password must contain at least one lowercase letter."
        elif not any(c.isdigit() for c in form_data["password"]):
            errors["password"] = "Password must contain at least one number."

        if not form_data["confirm_password"]:
            errors["confirm_password"] = "Please confirm your password."
        elif form_data["password"] != form_data["confirm_password"]:
            errors["confirm_password"] = "Passwords do not match."

        if not request.POST.get("terms"):
            errors["terms"] = "You must accept the Terms of Service and Privacy Policy."

        if errors:
            return render(request, "register.html", {
                "errors": errors,
                "form_data": form_data,
            })

        try:
            user = User.objects.create_user(
                username=form_data["username"],
                email=form_data["email"],
                password=form_data["password"],
                first_name=form_data["first_name"],
                last_name=form_data["last_name"],
            )

            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "user_type": form_data["user_type"],
                    "target_role": form_data["target_role"],
                },
            )
            if not created:
                profile.user_type = form_data["user_type"]
                profile.target_role = form_data["target_role"]
                profile.save(update_fields=["user_type", "target_role", "updated_at"])

            login(request, user)
            messages.success(request, f"Welcome {form_data['first_name']}! Your account has been created successfully.")
            return redirect("interviewapp:dashboard")

        except Exception as e:
            logger.exception("Registration error: %s", e)
            return render(request, "register.html", {
                "error": "An unexpected error occurred. Please try again.",
                "form_data": form_data,
            })

    return render(request, "register.html")


def user_login(request):
    if request.user.is_authenticated:
        return redirect("interviewapp:dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("interviewapp:dashboard")
        else:
            return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")


@login_required
def user_logout(request):
    logout(request)
    return redirect("interviewapp:login")


@login_required
def dashboard(request):
    sessions = InterviewSession.objects.filter(
        user=request.user
    ).order_by("-started_at")

    total_scores = []
    total_answered = 0

    for s in sessions:
        answered = s.answers.filter(processed=True).count()
        s.answered_done = answered
        total_answered += answered

        if s.total_questions > 0:
            s.progress_percent = int((answered / s.total_questions) * 100)
        else:
            s.progress_percent = 0

        if s.total_score is not None:
            total_scores.append(s.total_score)

    avg_score = round(sum(total_scores) / len(total_scores), 2) if total_scores else None

    return render(request, "dashboard.html", {
        "sessions": sessions,
        "avg_score": avg_score,
        "total_answered": total_answered,
    })


@login_required
def start_session(request):
    """
    Create an InterviewSession and prefill exactly n questions and Answer rows.
    Delegates creation and RAG generation to session_service.
    """
    if request.method == "POST":
        form = StartSessionForm(request.POST)
        if form.is_valid():
            raw_role = form.cleaned_data["role"]
            job_role = form.cleaned_data["job_role"]
            difficulty = int(form.cleaned_data["difficulty"])
            n = form.cleaned_data["n_questions"]

            session, created = create_standard_session(
                user=request.user,
                raw_role=raw_role,
                job_role=job_role,
                difficulty=difficulty,
                n_questions=n,
            )

            if created < n:
                messages.warning(request, f"Only created {created}/{n} questions for this session.")

            return redirect("interviewapp:next_question", session_id=session.id)
    else:
        role_param = request.GET.get("role", "").strip()
        initial_data = {}
        if role_param:
            initial_data["job_role"] = role_param.replace("-", " ").title()
            r_lower = role_param.lower()
            if any(k in r_lower for k in ["tech", "full-stack", "backend", "frontend", "devops", "data", "ai", "cyber"]):
                initial_data["role"] = "tech"
            elif any(k in r_lower for k in ["hr", "manager", "product", "people"]):
                initial_data["role"] = "hr"
        form = StartSessionForm(initial=initial_data)

    saved_resumes = Resume.objects.filter(user=request.user) if request.user.is_authenticated else []
    return render(request, "start.html", {"form": form, "saved_resumes": saved_resumes})


@login_required
def start_phase_practice(request):
    """
    Instantly create and launch an interview session for a specific roadmap phase.
    Delegates to session_service.create_phase_practice_session.
    """
    raw_role_param = request.GET.get("role", "Full-Stack Developer").strip()
    phase_num = request.GET.get("phase", "1").strip()
    phase_title = request.GET.get("phase_title", "").strip()

    session, created, job_role = create_phase_practice_session(
        user=request.user,
        raw_role_param=raw_role_param,
        phase_num=phase_num,
        phase_title=phase_title,
    )

    messages.success(request, f"Started Practice Session for {job_role}!")
    return redirect("interviewapp:next_question", session_id=session.id)


@login_required
def start_resume_jd_session(request):
    """
    Create and launch a tailored Mock Interview session based on uploaded/saved Resume & Job Description via RAG.
    Delegates to session_service.create_resume_jd_session.
    """
    if request.method != "POST":
        return redirect("interviewapp:start_session")

    selected_resume_id = request.POST.get("selected_resume_id", "").strip()
    resume_file = request.FILES.get("resume_file")
    if resume_file:
        try:
            validate_resume_file(resume_file)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("interviewapp:start_session")

    resume_title = request.POST.get("resume_title", "").strip()
    pasted_resume = request.POST.get("resume_text", "").strip()
    job_description = request.POST.get("job_description", "").strip()
    difficulty = int(request.POST.get("difficulty", "3"))
    n = int(request.POST.get("n_questions", "5"))

    resume_obj = None
    if selected_resume_id and selected_resume_id.isdigit():
        resume_obj = Resume.objects.filter(id=int(selected_resume_id), user=request.user).first()

    session, created = create_resume_jd_session(
        user=request.user,
        resume_obj=resume_obj,
        job_description=job_description,
        difficulty=difficulty,
        n_questions=n,
        resume_title=resume_title,
        resume_file=resume_file,
        pasted_resume=pasted_resume,
    )

    if not session:
        messages.error(request, "Please select a saved resume, upload a resume file, or provide a job description.")
        return redirect("interviewapp:start_session")

    messages.success(request, "Launched Resume & Job Description Tailored Session!")
    return redirect("interviewapp:next_question", session_id=session.id)


@login_required
def next_question(request, session_id):
    """
    Resolves next unanswered question for the session and renders interview.html.
    Delegates next question lookup to session_service.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden("This session does not belong to you.")

    if session.completed:
        return redirect("interviewapp:session_summary", session_id=session.id)

    next_ans = get_next_unprocessed_answer(session)
    if not next_ans:
        return redirect("interviewapp:session_summary", session_id=session.id)

    form = AnswerForm()
    return render(request, "interview.html", {
        "question": next_ans.question,
        "answer_id": next_ans.id,
        "form": form,
        "session": session,
    })


@login_required
def submit_answer(request, session_id):
    """
    Processes candidate answer submission, evaluation, and completion via answer_service.
    """
    if request.method != "POST":
        return redirect("interviewapp:next_question", session_id=session_id)

    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    answer_id = request.POST.get("answer_id")
    ans = get_object_or_404(Answer, id=answer_id, session=session)

    form = AnswerForm(request.POST, request.FILES)
    if form.is_valid():
        answer_text = form.data.get("answer_text", "").strip()
        audio_file = request.FILES.get("audio_file")

        try:
            ans, is_completed = submit_candidate_answer(
                session=session,
                answer_id=ans.id,
                answer_text=answer_text,
                audio_file=audio_file,
            )
        except (AnswerClaimError, AnswerDatabaseContentionError) as exc:
            logger.warning("Template answer submission contention for session #%s: %s", session.id, exc)
            session.refresh_from_db()
            if session.completed:
                return redirect("interviewapp:session_summary", session_id=session.id)
            return redirect("interviewapp:next_question", session_id=session.id)

        if is_completed:
            messages.success(request, "Interview completed successfully!")
            return redirect("interviewapp:session_summary", session_id=session.id)

        return redirect("interviewapp:next_question", session_id=session.id)

    return render(request, "interview.html", {
        "question": ans.question,
        "answer_id": ans.id,
        "form": form,
        "session": session,
    })


@login_required
@require_POST
def skip_question(request, session_id):
    """
    Skips current question via answer_service.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    try:
        ans, is_completed = skip_candidate_question(session)
    except (AnswerClaimError, AnswerDatabaseContentionError) as exc:
        logger.warning("Template skip question contention for session #%s: %s", session.id, exc)
        session.refresh_from_db()
        if session.completed:
            return redirect("interviewapp:session_summary", session_id=session.id)
        return redirect("interviewapp:next_question", session_id=session.id)

    if is_completed:
        messages.success(request, "Interview completed successfully!")
        return redirect("interviewapp:session_summary", session_id=session.id)

    return redirect("interviewapp:next_question", session_id=session.id)


@login_required
@require_POST
def end_session(request, session_id):
    """
    Terminates interview session immediately via answer_service.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    end_candidate_session(session)
    messages.success(request, "Interview completed successfully!")
    return redirect("interviewapp:session_summary", session_id=session.id)


@login_required
def session_summary(request, session_id):
    """
    Renders interview performance summary via session_service.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    context = get_session_summary_data(session)
    return render(request, "summary.html", context)


@login_required
def delete_session(request, session_id):
    """
    Deletes an interview session if owned by current user.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden("You are not allowed to delete this session.")

    if request.method == "POST":
        session.delete()
        messages.success(request, "Interview session deleted successfully.")
        return redirect("interviewapp:dashboard")

    return redirect("interviewapp:dashboard")


@login_required
def download_report(request, session_id):
    """
    Builds and downloads PDF executive report via report_service.
    """
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    pdf_buffer = build_session_pdf_report(session)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="AI_Interview_Report_{session.id}.pdf"'
    response.write(pdf_buffer.getvalue())
    pdf_buffer.close()
    return response


@require_POST
@login_required
def upload_frame(request):
    """
    Processes video frame analysis via video_service with completion guards and idempotency support.
    """
    frame = request.FILES.get("frame")
    session_id = request.POST.get("session_id")
    frame_id = request.POST.get("frame_id")

    if not frame or not session_id:
        return JsonResponse({"status": "error", "error": "Missing frame or session_id"}, status=400)

    try:
        sid = int(session_id)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "error": "Invalid session_id"}, status=400)

    session = InterviewSession.objects.filter(id=sid).first()
    if session is None:
        return JsonResponse({"status": "error", "error": "Session not found"}, status=404)
    if session.user_id != request.user.id:
        return JsonResponse({"status": "forbidden"}, status=403)
    if session.completed:
        return JsonResponse({"status": "error", "error": "Session is already completed"}, status=400)

    image_bytes = frame.read()
    result = process_video_frame(sid, image_bytes, frame_id=frame_id)
    if result.get("status") == "error":
        status_code = 503 if "busy" in result.get("error", "").lower() else 400
        return JsonResponse(result, status=status_code)
    return JsonResponse(result)


def roadmap_view(request):
    """
    Interactive Career & Skill Roadmap Generator view.
    """
    selected_role = request.GET.get("role", "full-stack").strip()
    experience_level = request.GET.get("level", "Intermediate").strip()

    roadmap_data = generate_ai_roadmap(selected_role, experience_level)

    popular_roles = [
        {"id": "full-stack", "title": "Full-Stack Developer", "category": "Development", "icon": "code"},
        {"id": "data-science", "title": "Data Scientist", "category": "Data & AI", "icon": "chart"},
        {"id": "frontend", "title": "Frontend Engineer", "category": "Development", "icon": "desktop"},
        {"id": "backend", "title": "Backend Engineer", "category": "Development", "icon": "server"},
        {"id": "devops", "title": "DevOps Specialist", "category": "Infrastructure", "icon": "cloud"},
        {"id": "product-manager", "title": "Product Manager", "category": "Product", "icon": "briefcase"},
        {"id": "ai-engineer", "title": "AI/ML Engineer", "category": "Data & AI", "icon": "sparkles"},
        {"id": "cybersecurity", "title": "Cyber Security Analyst", "category": "Security", "icon": "shield"},
    ]

    return render(request, "roadmap.html", {
        "roadmap": roadmap_data,
        "selected_role": selected_role,
        "experience_level": experience_level,
        "popular_roles": popular_roles,
    })


def generate_roadmap_api(request):
    """
    JSON API endpoint for generating custom AI roadmaps.
    """
    role = request.GET.get("role", "Full-Stack Developer").strip()
    level = request.GET.get("level", "Intermediate").strip()

    data = generate_ai_roadmap(role, level)
    return JsonResponse(data)
