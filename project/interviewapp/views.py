# interviewapp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import transaction
from django.utils import timezone
from django import forms
from .models import GeneratedQuestion, InterviewSession, Answer
from .forms import StartSessionForm, AnswerForm
from .nlp_utils import analyze_transcript
import hashlib
import logging
from django.contrib import messages
from .qgen_groq import generate_questions_groq, signature_of_text  # qgen_groq from earlier
from .views_helpers import generate_question_stub  # if you keep stub in a helper; otherwise use local stub
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
# from reportlab.lib.units import inch
from textwrap import wrap
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from .qgen_groq import generate_session_suggestions
from django.http import HttpResponse, HttpResponseForbidden

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
            # UserProfile.objects.create(
            #     user=user,
            #     user_type=form_data['user_type'],
            #     target_role=form_data['target_role']
            # )
            
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
    sessions = InterviewSession.objects.filter(user=request.user).order_by('-started_at')[:10]
    
    # Calculate average score
    total_scores = []
    total_answered = 0
    for s in sessions:
        total_answered += s.answered_count  # ✅ property access

        if s.total_score is not None:
            total_scores.append(s.total_score)

    avg_score = round(sum(total_scores) / len(total_scores), 2) if total_scores else None

    
    return render(request, 'dashboard.html', {
        'sessions': sessions,
        'avg_score': round(avg_score, 2) if avg_score else None,
        'total_answered': total_answered
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
            n = form.cleaned_data['n_questions']

            # create the session
            s = InterviewSession.objects.create(user=request.user, role=raw_role, total_score=None, current_index=0)

            created = 0
            attempts = 0
            max_attempts = max(50, n * 10)
            created_question_ids = []  # keep order of created questions

            # 1) Try LLM generation first
            try:
                llm_questions = generate_questions_groq(role=role_for_prompt, n=n, difficulty=3, model="llama-3.1-8b-instant")
            except Exception as e:
                logger.exception("Groq generation error: %s", e)
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
                        "difficulty": qobj.get("difficulty", 3),
                        "text": text,
                        "keywords": qobj.get("keywords", ""),
                        "source": "llm"
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
            s.answers.all().delete()
            idx = 1
            for qid in created_question_ids:
                qobj = GeneratedQuestion.objects.get(id=qid)
                Answer.objects.create(session=s, question=qobj, index=idx)
                idx += 1

            # 6) Redirect to the first question (next_question reads the next unprocessed answer)
            return redirect('interviewapp:next_question', session_id=s.id)
    else:
        form = StartSessionForm()

    return render(request, 'start.html', {'form': form})



@login_required
def next_question(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden("This session does not belong to you.")

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
        ans.answer_text = form.cleaned_data.get('answer_text', '').strip()

        result = analyze_transcript(ans.answer_text, ans.question)

        ans.score = result.get('score')
        ans.feedback = result.get('feedback', '')

        # ✅ THIS IS THE MISSING LINE
        ans.improvement_tips = result.get('improvement_tips', [])

        ans.processed = True
        ans.save()

        return redirect('interviewapp:next_question', session_id=session.id)

    return render(request, 'interview.html', {
        'question': ans.question,
        'answer_id': ans.id,
        'form': form,
        'session': session
    })
@login_required
def skip_question(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()
    
    # Mark current question as skipped (or create empty answer)
    used_q_ids = session.answers.values_list('question_id', flat=True)
    q = GeneratedQuestion.objects.filter(role=session.role).exclude(id__in=used_q_ids).first()
    
    if q:
        with transaction.atomic():
            session.current_index += 1
            session.save()
            Answer.objects.create(
                session=session, 
                question=q, 
                index=session.current_index,
                answer_text="[Skipped]",
                score=0
            )
    
    return redirect('interviewapp:next_question', session_id=session.id)

@login_required
def end_session(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()
    
    # Mark session as completed
    session.completed = True
    session.completed_at = timezone.now()
    session.save()
    
    messages.success(request, f"Interview session {session.id} completed!")
    return redirect('interviewapp:session_summary', session_id=session.id)



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
    # Save total_score but avoid saving suggestions here; we may persist later
    session.save(update_fields=['total_score'])

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
            suggestions = generate_session_suggestions(session, answer_payload, model="llama-3.1-8b-instant")
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

    # Render the template with both LLM suggestions and the simple parsed lists
    return render(request, 'summary.html', {
        'session': session,
        'answers': answers,
        'avg': round(avg, 2) if avg is not None else None,
        'duration': duration,
        'strengths': suggestions.get('strengths', strengths),
        'improvements': suggestions.get('improvements', improvements),
        'overall_tip': suggestions.get('overall_tip', ''),
        'resources': suggestions.get('resources', [])
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




@login_required
def download_report(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)

    # 🔒 Security check
    if session.user != request.user:
        return HttpResponseForbidden()

    answers = session.answers.select_related('question').all().order_by('index')

    # Recalculate average score (same logic as summary)
    scores = [a.score for a in answers if a.score is not None]
    avg = (sum(scores) / len(scores)) if scores else 0

    # Duration
    duration = 0
    if session.started_at and session.completed_at:
        duration = int((session.completed_at - session.started_at).total_seconds() / 60)

    # Suggestions (strengths, improvements, tips)
    suggestions = getattr(session, "suggestions_json", None) or {}

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Interview_Report_Session_{session.id}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    x_margin = 40
    y = height - 50

    def draw_block(text, y_pos, bold=False):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
        for line in wrap(text, 95):
            pdf.drawString(x_margin, y_pos, line)
            y_pos -= 14
        return y_pos

    # ================= TITLE =================
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(x_margin, y, "AI Mock Interview Report")
    y -= 35

    # ================= SESSION INFO =================
    y = draw_block(f"Candidate: {session.user.username}", y)
    y = draw_block(f"Role: {session.role}", y)
    y = draw_block(f"Date: {session.started_at.strftime('%d %b %Y')}", y)
    y = draw_block(f"Duration: {duration} minutes", y)
    y = draw_block(f"Average Score: {round(avg, 2)}/10", y)
    y -= 20

    # ================= QUESTIONS =================
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x_margin, y, "Question-wise Evaluation")
    y -= 20

    for idx, a in enumerate(answers, start=1):
        if y < 160:
            pdf.showPage()
            y = height - 50

        # Question
        y = draw_block(f"Q{idx}. {a.question.text}", y, bold=True)

        # Answer
        y = draw_block(
            f"Your Answer: {a.answer_text or 'No answer provided'}", y
        )

        # Score
        y = draw_block(f"Score: {a.score}/10", y)

        # Feedback
        y = draw_block(
            f"AI Feedback: {a.feedback or 'N/A'}", y
        )

        # ✅ Improvement Tips (IMPORTANT PART)
        tips = getattr(a, "improvement_tips", None)
        if tips:
            y = draw_block("Improvement Tips:", y, bold=True)

            if isinstance(tips, (list, tuple)):
                for tip in tips:
                    y = draw_block(f"- {tip}", y)
            else:
                y = draw_block(f"- {tips}", y)

        y -= 12

    # ================= OVERALL SUGGESTIONS =================
    if suggestions:
        if y < 220:
            pdf.showPage()
            y = height - 50

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(x_margin, y, "Performance Insights")
        y -= 20

        y = draw_block("Strengths:", y, bold=True)
        for s in suggestions.get("strengths", []):
            y = draw_block(f"- {s}", y)

        y -= 10
        y = draw_block("Improvements:", y, bold=True)
        for i in suggestions.get("improvements", []):
            y = draw_block(f"- {i}", y)

        y -= 10
        y = draw_block("Overall Tip:", y, bold=True)
        y = draw_block(suggestions.get("overall_tip", ""), y)

        y -= 10
        y = draw_block("Recommended Resources:", y, bold=True)
        for r in suggestions.get("resources", []):
            y = draw_block(f"- {r}", y)

    pdf.showPage()
    pdf.save()
    return response
