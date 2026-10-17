# interviewapp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.db import transaction
from django.utils import timezone
from django import forms
from django.conf import settings
from .models import GeneratedQuestion, InterviewSession, Answer, UserProfile, SessionQuestion
from .forms import StartSessionForm, AnswerForm
from .nlp_utils import analyze_transcript, generate_expected_answer
import hashlib
import logging
from django.contrib import messages
from .qgen_groq import generate_questions_groq, signature_of_text, generate_session_suggestions, generate_ai_roadmap, generate_resume_jd_questions_groq
from .views_helpers import generate_question_stub  # if you keep stub in a helper; otherwise use local stub

# RAG-augmented question generation (conditionally used)
try:
    from .rag import generate_questions_with_rag
    _rag_available = True
except ImportError:
    _rag_available = False
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from textwrap import wrap
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from .qgen_groq import generate_session_suggestions
from django.http import HttpResponse, HttpResponseForbidden
from .speech_utils import transcribe_audio
from django.http import JsonResponse
from interviewapp.video_behavior_utils import analyze_eye_contact_and_head
from interviewapp.video_summary_utils import compute_video_confidence
from interviewapp.video_ai_feedback import generate_video_behavior_feedback
from collections import defaultdict
from interviewapp.video_utils import count_faces

ROLE_MAP = {
    'tech': 'Technical',
    'hr': 'Human Resources',
    'apt': 'Aptitude',
    'beh': 'Behavioral',
}

def home_page(request):
    return render(request, 'home.html')



def generate_question_stub(role, difficulty=3):
    """
    Generate a question stub based on the role and difficulty.
    """
    role_instructions = {
        "tech": "Explain a core technical concept or solve a coding problem.",
        "hr": "Describe how to handle workplace scenarios or HR policies.",
        "aptitude": "Solve a logical reasoning or quantitative problem.",
        "behavioral": "Discuss how to handle interpersonal or situational challenges."
    }

    instruction = role_instructions.get(role.lower(), "Provide a general question related to the role.")
    text = f"(AI stub) {role} question (difficulty {difficulty}): {instruction}"
    keywords = instruction.lower().replace(" or ", ",").replace(" ", ",")

    return {"text": text, "keywords": keywords, "difficulty": difficulty}

def signature_of_text(text):
    norm = " ".join(text.lower().split())
    return hashlib.sha256(norm.encode()).hexdigest()


def register(request):
    """
    Handle user registration with proper error handling
    """
    if request.user.is_authenticated:
        return redirect('interviewapp:dashboard')

    if request.method == 'POST':
        # Get form data
        form_data = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'username': request.POST.get('username', '').strip(),
            'password': request.POST.get('password', '').strip(),
            'confirm_password': request.POST.get('confirm_password', '').strip(),
            'user_type': request.POST.get('user_type', 'student'),
            'target_role': request.POST.get('target_role', ''),
        }
        
        errors = {}
        
        # Validation
        if not form_data['first_name']:
            errors['first_name'] = 'First name is required.'
        
        if not form_data['last_name']:
            errors['last_name'] = 'Last name is required.'
        
        if not form_data['email']:
            errors['email'] = 'Email address is required.'
        elif not '@' in form_data['email']:
            errors['email'] = 'Please enter a valid email address.'
        elif User.objects.filter(email=form_data['email']).exists():
            errors['email'] = 'This email is already registered.'
        
        if not form_data['username']:
            errors['username'] = 'Username is required.'
        elif len(form_data['username']) < 3:
            errors['username'] = 'Username must be at least 3 characters.'
        elif User.objects.filter(username=form_data['username']).exists():
            errors['username'] = 'This username is already taken.'
        
        if not form_data['password']:
            errors['password'] = 'Password is required.'
        elif len(form_data['password']) < 8:
            errors['password'] = 'Password must be at least 8 characters.'
        elif not any(c.isupper() for c in form_data['password']):
            errors['password'] = 'Password must contain at least one uppercase letter.'
        elif not any(c.islower() for c in form_data['password']):
            errors['password'] = 'Password must contain at least one lowercase letter.'
        elif not any(c.isdigit() for c in form_data['password']):
            errors['password'] = 'Password must contain at least one number.'
        
        if not form_data['confirm_password']:
            errors['confirm_password'] = 'Please confirm your password.'
        elif form_data['password'] != form_data['confirm_password']:
            errors['confirm_password'] = 'Passwords do not match.'
        
        if not request.POST.get('terms'):
            errors['terms'] = 'You must accept the Terms of Service and Privacy Policy.'
        
        if errors:
            # Return form with errors and preserved data
            return render(request, 'register.html', {
                'errors': errors,
                'form_data': form_data
            })
        
        try:
            # Create user
            user = User.objects.create_user(
                username=form_data['username'],
                email=form_data['email'],
                password=form_data['password'],
                first_name=form_data['first_name'],
                last_name=form_data['last_name']
            )
            
            # Optional: Create UserProfile
            UserProfile.objects.create(
                user=user,
                user_type=form_data['user_type'],
                target_role=form_data['target_role']
            )
            
            # Log the user in
            login(request, user)
            
            # Success message
            messages.success(request, f"Welcome {form_data['first_name']}! Your account has been created successfully.")
            
            # Redirect to dashboard
            return redirect('interviewapp:dashboard')
            
        except Exception as e:
            # Log the error for debugging
            print(f"Registration error: {e}")
            
            # User-friendly error message
            return render(request, 'register.html', {
                'error': 'An unexpected error occurred. Please try again.',
                'form_data': form_data
            })
    
    # GET request - show empty registration form
    return render(request, 'register.html')

def user_login(request):
    if request.user.is_authenticated:
        return redirect('interviewapp:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('interviewapp:dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('interviewapp:login')
@login_required
def dashboard(request):
    sessions = InterviewSession.objects.filter(
        user=request.user
    ).order_by('-started_at')

    total_scores = []
    total_answered = 0

    for s in sessions:
        answered = s.answers.filter(processed=True).count()

        # ✅ SAFE runtime attributes
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
        "total_answered": total_answered
    })


logger = logging.getLogger(__name__)


# Replace the start_session function in interviewapp/views.py with this:
@login_required
def start_session(request):
    """
    Create an InterviewSession and prefill exactly n questions and corresponding Answer rows.
    Ensures this session will only ever use the created n questions.
    """
    if request.method == 'POST':
        form = StartSessionForm(request.POST)
        if form.is_valid():
            raw_role = form.cleaned_data['role']               # DB key (e.g. 'tech')
            role_for_prompt = ROLE_MAP.get(raw_role.lower(), raw_role.capitalize())
            job_role = form.cleaned_data['job_role']
            difficulty = int(form.cleaned_data['difficulty'])
            n = form.cleaned_data['n_questions']

            # create the session
            s = InterviewSession.objects.create(
                user=request.user, 
                total_questions=n, 
                role=raw_role, 
                job_role=job_role, 
                difficulty=difficulty,
                total_score=None, 
                current_index=0
            )

            # Fetch up to 15 unique question texts previously asked to the user in this round type
            from .models import SessionQuestion
            prev_questions = list(SessionQuestion.objects.filter(
                session__user=request.user,
                session__role=raw_role
            ).order_by('-id').values_list('question__text', flat=True).distinct()[:15])

            created = 0
            attempts = 0
            max_attempts = max(50, n * 10)
            created_question_ids = []  # keep order of created questions

            # 1) Try LLM generation first (RAG or standard Groq)
            rag_enabled = getattr(settings, 'RAG_ENABLED', False) and _rag_available
            question_source = "rag" if rag_enabled else "llm"
            try:
                if rag_enabled:
                    llm_questions = generate_questions_with_rag(
                        role=role_for_prompt,
                        job_role=job_role,
                        n=n,
                        difficulty=difficulty,
                        previous_questions=prev_questions
                    )
                else:
                    llm_questions = generate_questions_groq(
                        role=role_for_prompt, 
                        job_role=job_role, 
                        n=n, 
                        difficulty=difficulty, 
                        previous_questions=prev_questions
                    )
            except Exception as e:
                logger.exception("Question generation error (rag=%s): %s", rag_enabled, e)
                messages.warning(request, "AI question generation temporarily failed — using fallback questions.")
                llm_questions = []

            # 2) Save unique LLM questions to DB (but attach only IDs to this session)
            for qobj in llm_questions:
                if created >= n:
                    break
                text = qobj.get("text", "").strip()
                if not text:
                    continue
                sig = signature_of_text(text)
                # If a DB row with same signature exists, reuse that question row (but still include it in session)
                qrow, _ = GeneratedQuestion.objects.get_or_create(
                    signature=sig,
                    defaults={
                        "role": raw_role,
                        "difficulty": qobj.get("difficulty", 2),
                        "text": text,
                        "keywords": qobj.get("keywords", ""),
                        "source": question_source
                    }
                )
                # ensure role stored is the raw_role key so session lookups remain consistent
                if qrow.role != raw_role:
                    qrow.role = raw_role
                    qrow.save(update_fields=["role"])

                created_question_ids.append(qrow.id)
                created += 1

            # 3) If still need more, create fallback stub questions
            while created < n and attempts < max_attempts:
                attempts += 1
                payload = generate_question_stub(raw_role, difficulty=2)
                text = payload.get('text', '').strip()
                if not text:
                    continue
                sig = signature_of_text(text)
                qrow, created_new = GeneratedQuestion.objects.get_or_create(
                    signature=sig,
                    defaults={
                        "role": raw_role,
                        "difficulty": payload.get("difficulty", 3),
                        "text": text,
                        "keywords": payload.get("keywords", ""),
                        "source": "template"
                    }
                )
                # If we already had the signature, but the role differs, ensure consistency:
                if qrow.role != raw_role:
                    qrow.role = raw_role
                    qrow.save(update_fields=["role"])

                # if this qrow already in our session list, skip (we want n unique entries)
                if qrow.id in created_question_ids:
                    continue

                created_question_ids.append(qrow.id)
                created += 1

            # 4) If created < n still, warn user (but proceed with whatever created)
            if created < n:
                messages.warning(request, f"Only created {created}/{n} questions for this session.")

            # 5) Create Answer placeholders in the exact order for this session
            # remove any existing answers for this session (defensive)
# 5) Create Answer placeholders in the exact order for this session
            s.answers.all().delete()
            idx = 1
            for qid in created_question_ids:
                qobj = GeneratedQuestion.objects.get(id=qid)
                Answer.objects.create(session=s, question=qobj, index=idx)
                idx += 1

            # ✅ ADD THIS LINE (CRITICAL)
            s.total_questions = len(created_question_ids)
            s.current_index = 1   # first question index (matches Answer.index)
            s.save(update_fields=["total_questions", "current_index"])
            # 6) Redirect to the first question (next_question reads the next unprocessed answer)
            return redirect('interviewapp:next_question', session_id=s.id)
    else:
        role_param = request.GET.get('role', '').strip()
        initial_data = {}
        if role_param:
            initial_data['job_role'] = role_param.replace('-', ' ').title()
            r_lower = role_param.lower()
            if any(k in r_lower for k in ['tech', 'full-stack', 'backend', 'frontend', 'devops', 'data', 'ai', 'cyber']):
                initial_data['role'] = 'tech'
            elif any(k in r_lower for k in ['hr', 'manager', 'product', 'people']):
                initial_data['role'] = 'hr'
        form = StartSessionForm(initial=initial_data)

    return render(request, 'start.html', {'form': form})


@login_required
def start_phase_practice(request):
    """
    Instantly create and launch an interview session for a specific roadmap phase.
    """
    raw_role_param = request.GET.get('role', 'Full-Stack Developer').strip()
    phase_num = request.GET.get('phase', '1').strip()
    phase_title = request.GET.get('phase_title', '').strip()
    
    job_role = f"{raw_role_param.replace('-', ' ').title()}"
    if phase_title:
        job_role += f" (Phase {phase_num}: {phase_title})"
    
    r_lower = raw_role_param.lower()
    raw_role = 'tech'
    if any(k in r_lower for k in ['hr', 'manager', 'people']):
        raw_role = 'hr'
    elif any(k in r_lower for k in ['apt', 'logic', 'math']):
        raw_role = 'apt'
        
    role_for_prompt = ROLE_MAP.get(raw_role, "Technical")
    difficulty = 3
    n = 5

    s = InterviewSession.objects.create(
        user=request.user,
        total_questions=n,
        role=raw_role,
        job_role=job_role,
        difficulty=difficulty,
        total_score=None,
        current_index=0
    )

    prev_questions = list(SessionQuestion.objects.filter(
        session__user=request.user,
        session__role=raw_role
    ).order_by('-id').values_list('question__text', flat=True).distinct()[:15])

    rag_enabled = getattr(settings, 'RAG_ENABLED', False) and _rag_available
    question_source = "rag" if rag_enabled else "llm"
    try:
        if rag_enabled:
            llm_questions = generate_questions_with_rag(
                role=role_for_prompt,
                job_role=job_role,
                n=n,
                difficulty=difficulty,
                previous_questions=prev_questions
            )
        else:
            llm_questions = generate_questions_groq(
                role=role_for_prompt,
                job_role=job_role,
                n=n,
                difficulty=difficulty,
                previous_questions=prev_questions
            )
    except Exception as e:
        logger.exception("Groq phase generation error (rag=%s): %s", rag_enabled, e)
        llm_questions = []

    created_question_ids = []
    created = 0

    for qobj in llm_questions:
        if created >= n:
            break
        text = qobj.get("text", "").strip()
        if not text:
            continue
        sig = signature_of_text(text)
        qrow, _ = GeneratedQuestion.objects.get_or_create(
            signature=sig,
            defaults={
                "role": raw_role,
                "difficulty": qobj.get("difficulty", 3),
                "text": text,
                "keywords": qobj.get("keywords", ""),
                "source": question_source
            }
        )
        created_question_ids.append(qrow.id)
        created += 1

    attempts = 0
    while created < n and attempts < 20:
        attempts += 1
        payload = generate_question_stub(raw_role, difficulty=3)
        text = payload.get('text', '').strip()
        if not text:
            continue
        sig = signature_of_text(text)
        qrow, _ = GeneratedQuestion.objects.get_or_create(
            signature=sig,
            defaults={
                "role": raw_role,
                "difficulty": 3,
                "text": text,
                "keywords": payload.get("keywords", ""),
                "source": "template"
            }
        )
        if qrow.id not in created_question_ids:
            created_question_ids.append(qrow.id)
            created += 1

    s.answers.all().delete()
    idx = 1
    for qid in created_question_ids:
        qobj = GeneratedQuestion.objects.get(id=qid)
        Answer.objects.create(session=s, question=qobj, index=idx)
        idx += 1

    s.total_questions = len(created_question_ids)
    s.current_index = 1
    s.save(update_fields=["total_questions", "current_index"])

    messages.success(request, f"Started Practice Session for {job_role}!")
    return redirect('interviewapp:next_question', session_id=s.id)



@login_required
def next_question(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden("This session does not belong to you.")

    if session.completed:
        return redirect('interviewapp:session_summary', session_id=session.id)

    # find the next Answer placeholder for this session that is not processed
    # prefer 'processed' flag, or if you use answer_text, use answer_text=''
    next_ans = session.answers.filter(processed=False).order_by('index').first()
    if not next_ans:
        # no more questions -> go to summary
        return redirect('interviewapp:session_summary', session_id=session.id)

    # update session.current_index to reflect current progress
    session.current_index = next_ans.index
    session.save(update_fields=['current_index'])

    # Render the question page for this Answer
    form = AnswerForm()
    return render(request, 'interview.html', {
        'question': next_ans.question,
        'answer_id': next_ans.id,
        'form': form,
        'session': session
    })


@login_required
def submit_answer(request, session_id):
    if request.method != 'POST':
        return redirect('interviewapp:next_question', session_id=session_id)

    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    answer_id = request.POST.get('answer_id')
    ans = get_object_or_404(Answer, id=answer_id, session=session)

    form = AnswerForm(request.POST, request.FILES)
    if form.is_valid():
        ans.answer_text = form.data.get('answer_text', '').strip() #fixed this problem 
        ans.audio_file = request.FILES.get('audio_file')

        # ✅ SAVE FIRST so audio exists on disk
        ans.save(update_fields=['answer_text', 'audio_file'])


        # 🎙 Transcribe audio if uploaded AND text is empty
        if ans.audio_file and not ans.answer_text:
            transcribed = transcribe_audio(ans.audio_file.path)
            ans.answer_text = transcribed or "[Voice answer could not be transcribed]"

        # 🧠 Analyze answer
        result = analyze_transcript(ans.answer_text, ans.question)

        ans.score = result.get('score')
        ans.feedback = result.get('feedback', '')
        ans.improvement_tips = result.get('improvement_tips', [])
        ans.processed = True

        # ✅ Final save once
        ans.save(update_fields=[
            'answer_text',
            'score',
            'feedback',
            'improvement_tips',
            'processed'
        ])

        # 🔥 AUTO END SESSION
# Decide next step based on remaining unprocessed answers
        remaining = session.answers.filter(processed=False).exists()

        if not remaining:
            # 🔥 SAVE VIDEO STATS BEFORE COMPLETION
            video_stats = SESSION_VIDEO_STATS.get(str(session.id))

            if video_stats:
                session.video_stats_json = video_stats

                video_summary = compute_video_confidence(video_stats)

                session.video_feedback_json = generate_video_behavior_feedback(
                    role=session.role,
                    confidence_score=video_summary["confidence_score"],
                    presence_pct=video_summary["presence_pct"],
                    eye_contact_pct=video_summary["eye_contact_pct"],
                    movement_pct=video_summary["movement_pct"]
                )

            session.completed = True
            session.completed_at = timezone.now()
            session.save()

            messages.success(request, "Interview completed successfully!")
            return redirect("interviewapp:session_summary", session_id=session.id)

        return redirect("interviewapp:next_question", session_id=session.id)



    return render(request, 'interview.html', {
        'question': ans.question,
        'answer_id': ans.id,
        'form': form,
        'session': session
    })


    
@login_required
@require_POST
def skip_question(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()
    
    # Mark current unprocessed answer placeholder as skipped
    current_ans = session.answers.filter(processed=False).order_by('index').first()
    
    if current_ans:
        with transaction.atomic():
            current_ans.answer_text = "[Skipped]"
            current_ans.score = 0
            current_ans.feedback = "Question was skipped."
            current_ans.processed = True
            current_ans.save()

            remaining = session.answers.filter(processed=False).exists()
            if not remaining:
                video_stats = SESSION_VIDEO_STATS.get(str(session.id))
                if video_stats:
                    session.video_stats_json = video_stats
                    video_summary = compute_video_confidence(video_stats)
                    session.video_feedback_json = generate_video_behavior_feedback(
                        role=session.role,
                        confidence_score=video_summary["confidence_score"],
                        presence_pct=video_summary["presence_pct"],
                        eye_contact_pct=video_summary["eye_contact_pct"],
                        movement_pct=video_summary["movement_pct"]
                    )
                session.completed = True
                session.completed_at = timezone.now()
                session.save()
                messages.success(request, "Interview completed successfully!")
                return redirect("interviewapp:session_summary", session_id=session.id)
    
    return redirect('interviewapp:next_question', session_id=session.id)

@login_required
@require_POST
def end_session(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    # ✅ FETCH IN-MEMORY VIDEO STATS
    video_stats = SESSION_VIDEO_STATS.get(str(session.id))

    if video_stats:
        # ✅ SAVE RAW STATS
        session.video_stats_json = video_stats

        # ✅ COMPUTE SUMMARY
        video_summary = compute_video_confidence(video_stats)

        # ✅ GENERATE AI FEEDBACK ONCE
        video_feedback = generate_video_behavior_feedback(
            role=session.role,
            confidence_score=video_summary["confidence_score"],
            presence_pct=video_summary["presence_pct"],
            eye_contact_pct=video_summary["eye_contact_pct"],
            movement_pct=video_summary["movement_pct"]
        )

        session.video_feedback_json = video_feedback

    session.completed = True
    session.completed_at = timezone.now()
    session.save()

    messages.success(request, "Interview completed successfully!")
    return redirect("interviewapp:session_summary", session_id=session.id)




@login_required
def session_summary(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    # fetch answers and compute avg
    answers = session.answers.select_related('question').all().order_by('index')
    scores = [a.score for a in answers if a.score is not None]
    avg = (sum(scores) / len(scores)) if scores else None
    session.total_score = avg
    session.save(update_fields=['total_score'])

    # Populate expected answers for unanswered/skipped questions
    for a in answers:
        is_unanswered = (not a.answer_text) or (a.answer_text.strip() in ["", "[Skipped]", "[Voice answer could not be transcribed]", "No answer provided"]) or (a.score == 0)
        a.is_unanswered = is_unanswered
        if a.question and not a.expected_answer:
            try:
                keywords_list = [k.strip() for k in a.question.keywords.split(',')] if a.question.keywords else []
                exp = generate_expected_answer(a.question.text, session.role, keywords_list)
                a.expected_answer = exp
                a.save(update_fields=['expected_answer'])
            except Exception:
                pass

    # Calculate Breakdown Metrics (excluding skipped/empty answers)
    total_q = answers.count()
    attempted_answers = answers.exclude(answer_text__in=["[Skipped]", "", "[Voice answer could not be transcribed]"])
    attempted_count = attempted_answers.count()
    completion_rate = int((attempted_count / total_q) * 100) if total_q else 0
    
    attempted_scores = [a.score for a in attempted_answers if a.score is not None]
    content_quality_score = (sum(attempted_scores) / len(attempted_scores)) if attempted_scores else 0

    # duration (minutes) — uses session.completed_at if present
    duration = 0
    if session.started_at and getattr(session, 'completed_at', None):
        duration = int((session.completed_at - session.started_at).total_seconds() / 60)

    # lightweight strengths/improvements extraction from answer.feedback (keeps your original behavior)
    strengths = []
    improvements = []
    for answer in answers:
        fb = (answer.feedback or "").lower()
        text_snippet = answer.question.text[:70] + ("..." if len(answer.question.text) > 70 else "")
        if fb:
            if 'good' in fb or 'excellent' in fb or 'well' in fb:
                strengths.append(f"Strong answer to: {text_snippet}")
            if 'improv' in fb or 'better' in fb or 'need' in fb:
                improvements.append(f"Could improve: {text_snippet}")

    strengths = list(dict.fromkeys(strengths))[:3]     # preserve order, dedupe, limit
    improvements = list(dict.fromkeys(improvements))[:5]

    # Build the simple answers list to send to the LLM helper
    answer_payload = []
    for a in answers:
        answer_payload.append({
            "question_text": a.question.text,
            "answer_text": a.answer_text or "",
            "score": a.score if a.score is not None else 0,
            "feedback": a.feedback or ""
        })

    # If suggestions were previously saved on the session, use them; otherwise generate
    suggestions = getattr(session, "suggestions_json", None) or None

    if not suggestions:
        try:
            suggestions = generate_session_suggestions(session, answer_payload)
            # If the model returned something unexpected, ensure keys exist
            if not isinstance(suggestions, dict):
                suggestions = None
        except Exception as e:
            # LLM failed — fallback to simple heuristics (use strengths/improvements we built)
            suggestions = None
            logger = logging.getLogger(__name__)
            logger.exception("Suggestion generation failed: %s", e)

    # If suggestions exist and session model supports persisting them, save once
    if suggestions and hasattr(session, "suggestions_json"):
        try:
            # Save suggestions atomically
            with transaction.atomic():
                session.suggestions_json = suggestions
                session.save(update_fields=["suggestions_json"])
        except Exception:
            # ignore save errors (DB migration might not exist); keep suggestions ephemeral
            pass

    # If suggestions missing, create harmless defaults
    if not suggestions:
        suggestions = {
            "strengths": strengths or ["Clear answers to some questions."],
            "improvements": improvements or ["Work on structuring answers and giving concrete examples."],
            "overall_tip": "Practice concise explanations, and focus on weaker areas identified above.",
            "resources": ["Review domain fundamentals", "Practice mock interviews", "Study common patterns"]
        }
        print(session.total_score)


    #video_stats = SESSION_VIDEO_STATS.get(str(session.id))

    video_summary = None
    video_ai_feedback = None

    if session.video_stats_json:
        video_summary = compute_video_confidence(session.video_stats_json)

    if session.video_feedback_json:
        video_ai_feedback = session.video_feedback_json

    # if video_summary:
    #     video_ai_feedback = generate_video_behavior_feedback(
    #         role=session.role,
    #         confidence_score=video_summary["confidence_score"],
    #         presence_pct=video_summary["presence_pct"],
    #         eye_contact_pct=video_summary["eye_contact_pct"],
    #         movement_pct=video_summary["movement_pct"]
    #     )

    # Render the template with both LLM suggestions and the simple parsed lists
    return render(request, 'summary.html', {
        'session': session,
        'answers': answers,
        'avg': round(avg, 2) if avg is not None else None,
        'content_quality_score': content_quality_score,
        'completion_rate': completion_rate,
        'duration': duration,
        'strengths': suggestions.get('strengths', strengths),
        'improvements': suggestions.get('improvements', improvements),
        'overall_tip': suggestions.get('overall_tip', ''),
        'resources': suggestions.get('resources', []),
        "video_summary": video_summary,
        "video_ai_feedback": video_ai_feedback
    })

class SimpleStartForm(forms.Form):
    role = forms.ChoiceField(
        choices=[
            ('Software Engineer', 'Software Engineer'),
            ('Product Manager', 'Product Manager'),
            ('Data Scientist', 'Data Scientist'),
            ('UX Designer', 'UX Designer'),
        ],
        widget=forms.RadioSelect
    )
    n_questions = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=5,
        widget=forms.HiddenInput()  # Or use NumberInput
    )

# @login_required
# def start_session_simple(request):
#     """
#     Minimal working version for testing
#     """
#     if request.method == 'POST':
#         form = SimpleStartForm(request.POST)
#         if form.is_valid():
#             role = form.cleaned_data['role']
#             n = form.cleaned_data['n_questions']
            
#             # Create session
#             session = InterviewSession.objects.create(
#                 user=request.user,
#                 role=role,
#                 total_questions=n
#             )
            
#             # Create simple questions without AI
#             for i in range(n):
#                 text = f"{role} Question {i+1}: Describe your experience with relevant technologies."
#                 sig = signature_of_text(text)
                
#                 if not GeneratedQuestion.objects.filter(signature=sig).exists():
#                     GeneratedQuestion.objects.create(
#                         role=role,
#                         difficulty=3,
#                         text=text,
#                         keywords=f"{role},experience,technologies",
#                         signature=sig,
#                         source='manual'
#                     )
            
#             messages.success(request, f"Interview session started with {n} questions!")
#             return redirect('interviewapp:next_question', session_id=session.id)
#     else:
#         form = SimpleStartForm()
    
#     return render(request, 'start.html', {'form': form})





@login_required
def delete_session(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)

    # 🔒 Permission check
    if session.user != request.user:
        return HttpResponseForbidden("You are not allowed to delete this session.")

    # Allow only POST (safety)
    if request.method == "POST":
        session.delete()
        messages.success(request, "Interview session deleted successfully.")
        return redirect("interviewapp:dashboard")

    # If GET request → redirect (avoid accidental deletes)
    return redirect("interviewapp:dashboard")




import json
from io import BytesIO
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, HRFlowable

@login_required
def download_report(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()

    # Data Calculations
    answers = session.answers.select_related('question').all().order_by('index')
    scores = [a.score for a in answers if a.score is not None]
    avg = (sum(scores) / len(scores)) if scores else 0
    duration = int((session.completed_at - session.started_at).total_seconds() / 60) if (session.completed_at and session.started_at) else 0
    report_date = session.completed_at or session.started_at or timezone.now()

    # Calculate Breakdown Metrics (excluding skipped/empty answers)
    total_q = answers.count()
    attempted_answers = answers.exclude(answer_text__in=["[Skipped]", "", "[Voice answer could not be transcribed]"])
    attempted_count = attempted_answers.count()
    completion_rate = int((attempted_count / total_q) * 100) if total_q else 0
    
    attempted_scores = [a.score for a in attempted_answers if a.score is not None]
    content_quality_score = (sum(attempted_scores) / len(attempted_scores)) if attempted_scores else 0
    
    # PDF Setup
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="AI_Interview_Report_{session.id}.pdf"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=50, leftMargin=50, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    elements = []

    # --- Professional Color Palette ---
    BRAND_INDIGO = colors.HexColor("#4F46E5")
    TEXT_DARK = colors.HexColor("#1E293B")
    TEXT_LIGHT = colors.HexColor("#64748B")
    BG_SLATE = colors.HexColor("#F8FAFC")
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # --- Custom Paragraph Styles ---
    h1_style = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=22, textColor=TEXT_DARK, spaceAfter=2)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, textColor=BRAND_INDIGO, spaceBefore=15, spaceAfter=10, borderPadding=5)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, textColor=TEXT_DARK, leading=14)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=8, textColor=TEXT_LIGHT, fontName="Helvetica-Bold", leading=10)
    quote_style = ParagraphStyle('Quote', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#475569"), fontName="Helvetica-Oblique", leftIndent=15, leading=14)

    # ================= 1. BRANDED HEADER =================
    header_data = [
        [Paragraph("MockInterview<font color='#4F46E5'>.ai</font>", h1_style), 
         Paragraph(f"REPORT ID: #{session.id}<br/>DATE: {report_date.strftime('%d %b %Y')}", label_style)]
    ]
    header_tab = Table(header_data, colWidths=[350, 150])
    header_tab.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
    elements.append(header_tab)
    elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_INDIGO, spaceBefore=5, spaceAfter=20))

    # ================= 2. EXECUTIVE SUMMARY CARD =================
    elements.append(Paragraph("EXECUTIVE SUMMARY", label_style))
    summary_data = [
        [
            Paragraph("CANDIDATE", label_style), 
            Paragraph("TARGET ROLE", label_style), 
            Paragraph("ANSWER QUALITY", label_style),
            Paragraph("COMPLETION RATE", label_style),
            Paragraph("OVERALL SCORE", label_style)
        ],
        [
            Paragraph(session.user.get_full_name().upper(), body_style), 
            Paragraph(session.role.upper(), body_style), 
            Paragraph(f"<b>{round(content_quality_score, 1)}</b>/100", body_style),
            Paragraph(f"<b>{completion_rate}%</b>", body_style),
            Paragraph(f"<font size='12' color='#4F46E5'><b>{round(avg, 1)}</b></font><font size='8' color='#94A3B8'> / 100</font>", body_style)
        ]
    ]
    summary_tab = Table(summary_data, colWidths=[100, 105, 100, 95, 95])
    summary_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_SLATE),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 15),
    ]))
    elements.append(summary_tab)
    elements.append(Spacer(1, 25))

    # ================= 3. PERFORMANCE LOG =================
    elements.append(Paragraph("QUESTION-BY-QUESTION ANALYSIS", h2_style))

    for idx, a in enumerate(answers, start=1):
        q_container = []
        
        # Determine status color
        score = a.score or 0
        status_color = "#22C55E" if score >= 80 else "#F59E0B" if score >= 60 else "#EF4444"
        status_text = "EXCEPTIONAL" if score >= 80 else "SATISFACTORY" if score >= 60 else "NEEDS FOCUS"

        # Question Header Table
        q_head_data = [[
            Paragraph(f"<font color='#94A3B8'>QUESTION {idx}</font>", label_style),
            Paragraph(f"<font color='{status_color}'>● {status_text}</font>", label_style)
        ]]
        q_head_tab = Table(q_head_data, colWidths=[400, 100])
        q_container.append(q_head_tab)
        
        # Question Content
        q_container.append(Paragraph(f"<b>{a.question.text}</b>", body_style))
        q_container.append(Spacer(1, 10))
        
        # Answer Block
        q_container.append(Paragraph("CANDIDATE RESPONSE", label_style))
        q_container.append(Paragraph(f"\"{a.answer_text or 'No response recorded.'}\"", quote_style))
        q_container.append(Spacer(1, 10))

        # Expected Answer Block (Model Solution)
        if a.expected_answer:
            q_container.append(Paragraph("EXPECTED ANSWER (MODEL SOLUTION)", label_style))
            q_container.append(Paragraph(a.expected_answer, ParagraphStyle('Expected', parent=body_style, leftIndent=10, textColor=colors.HexColor("#B45309"))))
            q_container.append(Spacer(1, 10))
        
        # AI Feedback Block
        q_container.append(Paragraph("AI EVALUATION", label_style))
        q_container.append(Paragraph(a.feedback or "Evaluation pending.", body_style))

        # Bulleted Tips
        if a.improvement_tips:
            q_container.append(Spacer(1, 5))
            for tip in a.improvement_tips:
                q_container.append(Paragraph(f"<font color='#4F46E5'>•</font> {tip}", ParagraphStyle('tip', parent=body_style, leftIndent=10, fontSize=9)))

        q_container.append(Spacer(1, 15))
        q_container.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR))
        q_container.append(Spacer(1, 15))
        
        elements.append(KeepTogether(q_container))

    # ================= 4. BEHAVIORAL INTELLIGENCE =================
    v_feedback = getattr(session, "video_feedback_json", None)
    if v_feedback:
        elements.append(PageBreak())
        elements.append(Paragraph("BEHAVIORAL INTELLIGENCE", h2_style))
        
        # Summary Paragraph
        elements.append(Paragraph(v_feedback.get("summary", ""), body_style))
        elements.append(Spacer(1, 15))

        # Strengths/Improvements Table
        b_data = [
            [Paragraph("CORE STRENGTHS", label_style), Paragraph("IMPROVEMENT AREAS", label_style)],
            [
                Paragraph("<br/>".join([f"<b>+</b> {s}" for s in v_feedback.get("strengths", [])]), body_style),
                Paragraph("<br/>".join([f"<b>-</b> {i}" for i in v_feedback.get("improvements", [])]), body_style)
            ]
        ]
        b_tab = Table(b_data, colWidths=[250, 250])
        b_tab.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (0,1), colors.HexColor("#F0FDF4")), # Light Green
            ('BACKGROUND', (1,0), (1,1), colors.HexColor("#FFF7ED")), # Light Orange
            ('PADDING', (0,0), (-1,-1), 12),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR)
        ]))
        elements.append(b_tab)

    # Build PDF
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


@require_POST
@login_required
def upload_frame(request):
    frame = request.FILES.get("frame")
    session_id = request.POST.get("session_id")

    if not frame or not session_id:
        return JsonResponse({"status": "error"}, status=400)

    try:
        sid = int(session_id)
    except (TypeError, ValueError):
        return JsonResponse({"status": "error"}, status=400)

    session = InterviewSession.objects.filter(id=sid).first()
    if session is None:
        return JsonResponse({"status": "error"}, status=404)
    if session.user_id != request.user.id:
        return JsonResponse({"status": "forbidden"}, status=403)

    image_bytes = frame.read()

    face_count = count_faces(image_bytes)
    behavior = analyze_eye_contact_and_head(image_bytes)

    stats = SESSION_VIDEO_STATS[session_id]
    stats["total_frames"] += 1

    if face_count > 0:
        stats["face_present_frames"] += 1

    if face_count > 1:
        stats["multiple_faces_frames"] += 1

    if behavior["eye_contact"]:
        stats["eye_contact_frames"] += 1

    if behavior["head_movement"]:
        stats["head_movement_frames"] += 1

    print(
        f"[SESSION {session_id}] "
        f"Face:{face_count} "
        f"Eye:{behavior['eye_contact']} "
        f"HeadMove:{behavior['head_movement']}"
    )
    # ✅ THIS LINE WAS MISSING
    return JsonResponse({
        "status": "ok",
        "faces": face_count,
        "eye_contact": behavior["eye_contact"],
        "head_movement": behavior["head_movement"]
    })




SESSION_VIDEO_STATS = defaultdict(lambda: {
    "total_frames": 0,
    "face_present_frames": 0,
    "multiple_faces_frames": 0,
    "eye_contact_frames": 0,
    "head_movement_frames": 0
})


def roadmap_view(request):
    """
    Interactive Career & Skill Roadmap Generator view.
    """
    selected_role = request.GET.get('role', 'full-stack').strip()
    experience_level = request.GET.get('level', 'Intermediate').strip()
    
    roadmap_data = generate_ai_roadmap(selected_role, experience_level)
    
    popular_roles = [
        {"id": "full-stack", "title": "Full-Stack Developer", "category": "Development", "icon": "code"},
        {"id": "data-science", "title": "Data Scientist", "category": "Data & AI", "icon": "chart"},
        {"id": "frontend", "title": "Frontend Engineer", "category": "Development", "icon": "desktop"},
        {"id": "backend", "title": "Backend Engineer", "category": "Development", "icon": "server"},
        {"id": "devops", "title": "DevOps Specialist", "category": "Infrastructure", "icon": "cloud"},
        {"id": "product-manager", "title": "Product Manager", "category": "Product", "icon": "briefcase"},
        {"id": "ai-engineer", "title": "AI/ML Engineer", "category": "Data & AI", "icon": "sparkles"},
        {"id": "cybersecurity", "title": "Cyber Security Analyst", "category": "Security", "icon": "shield"}
    ]
    
    return render(request, 'roadmap.html', {
        'roadmap': roadmap_data,
        'selected_role': selected_role,
        'experience_level': experience_level,
        'popular_roles': popular_roles
    })


def generate_roadmap_api(request):
    """
    JSON API endpoint for generating custom AI roadmaps.
    """
    role = request.GET.get('role', 'Full-Stack Developer').strip()
    level = request.GET.get('level', 'Intermediate').strip()
    
    data = generate_ai_roadmap(role, level)
    return JsonResponse(data)


def extract_text_from_resume_file(file_obj) -> str:
    """
    Extract raw text from uploaded PDF, TXT, or MD resume file.
    """
    if not file_obj:
        return ""
    
    filename = file_obj.name.lower()
    text = ""
    
    if filename.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(file_obj)
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            text = "\n".join(pages_text)
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to parse PDF resume with pypdf: %s", e)
            file_obj.seek(0)
            text = file_obj.read().decode('utf-8', errors='ignore')
    else:
        try:
            text = file_obj.read().decode('utf-8', errors='ignore')
        except Exception:
            text = ""

    return text.strip()


@login_required
def start_resume_jd_session(request):
    """
    Create and launch a tailored Mock Interview session based on uploaded Resume & Job Description.
    """
    if request.method != 'POST':
        return redirect('interviewapp:start_session')

    resume_file = request.FILES.get('resume_file')
    pasted_resume = request.POST.get('resume_text', '').strip()
    job_description = request.POST.get('job_description', '').strip()
    difficulty = int(request.POST.get('difficulty', '3'))
    n = int(request.POST.get('n_questions', '5'))

    # Extract resume text
    extracted_resume_text = extract_text_from_resume_file(resume_file) if resume_file else ""
    full_resume_text = (extracted_resume_text + "\n" + pasted_resume).strip()

    if not full_resume_text and not job_description:
        messages.error(request, "Please upload a resume file, paste your resume text, or provide a job description.")
        return redirect('interviewapp:start_session')

    job_role = "Resume & JD Specific Match"
    if job_description:
        lines = [l.strip() for l in job_description.splitlines() if l.strip()]
        if lines:
            job_role = f"Job Match: {lines[0][:45]}"

    # Create interview session
    s = InterviewSession.objects.create(
        user=request.user,
        total_questions=n,
        role='tech',
        job_role=job_role,
        difficulty=difficulty,
        total_score=None,
        current_index=0
    )

    try:
        llm_questions = generate_resume_jd_questions_groq(
            resume_text=full_resume_text,
            job_description=job_description,
            n=n,
            difficulty=difficulty
        )
    except Exception as e:
        logger.exception("Resume/JD question generation error: %s", e)
        llm_questions = []

    created_question_ids = []
    created = 0

    for qobj in llm_questions:
        if created >= n:
            break
        text = qobj.get("text", "").strip()
        if not text:
            continue
        sig = signature_of_text(text)
        qrow, _ = GeneratedQuestion.objects.get_or_create(
            signature=sig,
            defaults={
                "role": "tech",
                "difficulty": qobj.get("difficulty", difficulty),
                "text": text,
                "keywords": qobj.get("keywords", ""),
                "source": "llm"
            }
        )
        created_question_ids.append(qrow.id)
        created += 1

    attempts = 0
    while created < n and attempts < 20:
        attempts += 1
        payload = generate_question_stub('tech', difficulty=difficulty)
        text = payload.get('text', '').strip()
        if not text:
            continue
        sig = signature_of_text(text)
        qrow, _ = GeneratedQuestion.objects.get_or_create(
            signature=sig,
            defaults={
                "role": "tech",
                "difficulty": difficulty,
                "text": text,
                "keywords": payload.get("keywords", ""),
                "source": "template"
            }
        )
        if qrow.id not in created_question_ids:
            created_question_ids.append(qrow.id)
            created += 1

    s.answers.all().delete()
    idx = 1
    for qid in created_question_ids:
        qobj = GeneratedQuestion.objects.get(id=qid)
        Answer.objects.create(session=s, question=qobj, index=idx)
        idx += 1

    s.total_questions = len(created_question_ids)
    s.current_index = 1
    s.save(update_fields=["total_questions", "current_index"])

    messages.success(request, f"Launched Resume & Job Description Tailored Session!")
    return redirect('interviewapp:next_question', session_id=s.id)

