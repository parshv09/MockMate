# interviewapp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import transaction
from .models import GeneratedQuestion, InterviewSession, Answer
from .forms import StartSessionForm, AnswerForm
from .nlp_utils import analyze_transcript
import hashlib
import logging
from django.contrib import messages
from .qgen_groq import generate_questions_groq, signature_of_text  # qgen_groq from earlier
from .views_helpers import generate_question_stub  # if you keep stub in a helper; otherwise use local stub
def generate_question_stub(role, difficulty=3):
    text = f"(AI stub) {role} question (difficulty {difficulty}): Explain a core idea briefly."
    keywords = "explain,example,definition"
    return {"text": text, "keywords": keywords, "difficulty": difficulty}

def signature_of_text(text):
    norm = " ".join(text.lower().split())
    return hashlib.sha256(norm.encode()).hexdigest()

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
    return render(request, 'dashboard.html', {'sessions': sessions})



logger = logging.getLogger(__name__)


@login_required
def start_session(request):
    """
    Create an InterviewSession and prefetch `n_questions` using Groq (llama-3.1-8b-instant).
    Falls back to a template stub generator if Groq fails or doesn't produce enough unique questions.
    """
    if request.method == 'POST':
        form = StartSessionForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            n = form.cleaned_data['n_questions']
            # create the session
            s = InterviewSession.objects.create(user=request.user, role=role)

            created = 0
            # Safety caps
            max_attempts = max(50, n * 10)
            attempts = 0

            # 1) Try to get questions from Groq (llama-3.1-8b-instant)
            llm_questions = []
            try:
                # generate_questions_groq returns list of dicts: {'text','keywords','difficulty'}
                llm_questions = generate_questions_groq(role=role, n=n, difficulty=3, model="llama-3.1-8b-instant")
            except Exception as e:
                logger.exception("Groq generation error: %s", e)
                messages.warning(request, "AI question generation temporarily failed — using fallback questions.")

            # 2) Save unique questions from LLM output
            for qobj in llm_questions:
                if created >= n:
                    break
                text = qobj.get("text", "").strip()
                if not text:
                    continue
                sig = signature_of_text(text)
                if GeneratedQuestion.objects.filter(signature=sig).exists():
                    # duplicate, skip
                    continue
                GeneratedQuestion.objects.create(
                    role=role,
                    difficulty=qobj.get("difficulty", 3),
                    text=text,
                    keywords=qobj.get("keywords", ""),
                    signature=sig,
                    source='llm'
                )
                created += 1

            # 3) If we still need more questions, use the template stub generator until we reach n or hit max_attempts
            while created < n and attempts < max_attempts:
                attempts += 1
                try:
                    payload = generate_question_stub(role, difficulty=3)  # your existing stub function
                except Exception as e:
                    logger.exception("Fallback stub generation failed: %s", e)
                    break
                text = payload.get('text', '').strip()
                if not text:
                    continue
                sig = signature_of_text(text)
                if GeneratedQuestion.objects.filter(signature=sig).exists():
                    continue
                GeneratedQuestion.objects.create(
                    role=role,
                    difficulty=payload.get('difficulty', 3),
                    text=text,
                    keywords=payload.get('keywords', ''),
                    signature=sig,
                    source='template'
                )
                created += 1

            # 4) Inform user if we couldn't create the full requested number
            if created < n:
                messages.warning(request, f"Created {created}/{n} questions (some duplicates were skipped).")

            # 5) Redirect to the first question (next_question view handles no-question case)
            return redirect('interviewapp:next_question', session_id=s.id)
    else:
        form = StartSessionForm()

    return render(request, 'start.html', {'form': form})

@login_required
def next_question(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden("This session does not belong to you.")
    used_q_ids = session.answers.values_list('question_id', flat=True)
    q = GeneratedQuestion.objects.filter(role=session.role).exclude(id__in=used_q_ids).first()
    if not q:
        return redirect('interviewapp:session_summary', session_id=session.id)
    with transaction.atomic():
        session.current_index += 1
        session.save()
        ans = Answer.objects.create(session=session, question=q, index=session.current_index)
    form = AnswerForm()
    return render(request, 'interview.html', {'question': q, 'answer_id': ans.id, 'form': form, 'session': session})

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
        ans.answer_text = form.cleaned_data.get('answer_text','').strip()
        result = analyze_transcript(ans.answer_text, ans.question)
        ans.score = result['score']
        ans.feedback = result['feedback']
        ans.processed = True
        ans.save()
        return redirect('interviewapp:next_question', session_id=session.id)
    return render(request, 'interview.html', {'question': ans.question, 'answer_id': ans.id, 'form': form, 'session': session})

@login_required
def session_summary(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    if session.user != request.user:
        return HttpResponseForbidden()
    answers = session.answers.select_related('question').all().order_by('index')
    scores = [a.score for a in answers if a.score is not None]
    avg = sum(scores)/len(scores) if scores else None
    session.total_score = avg
    session.save()
    return render(request, 'summary.html', {'session': session, 'answers': answers, 'avg': avg})
