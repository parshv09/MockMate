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
ROLE_MAP = {
    'tech': 'Technical',
    'hr': 'Human Resources',
    'apt': 'Aptitude',
    'beh': 'Behavioral',
    # add any other possible keys your form sends
}

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
    for session in sessions:
        answers_with_score = session.answers.filter(score__isnull=False)
        if answers_with_score.exists():
            total_scores.append(sum(a.score for a in answers_with_score) / answers_with_score.count())
        total_answered += session.answers.count()
    
    avg_score = sum(total_scores) / len(total_scores) if total_scores else None
    
    return render(request, 'dashboard.html', {
        'sessions': sessions,
        'avg_score': round(avg_score, 2) if avg_score else None,
        'total_answered': total_answered
    })

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
            raw_role = form.cleaned_data['role']
            # normalize to human readable role for model prompt
            role_for_prompt = ROLE_MAP.get(raw_role.lower(), raw_role.capitalize())
            n = form.cleaned_data['n_questions']
            s = InterviewSession.objects.create(user=request.user, role=raw_role, total_questions=n )
             # DEBUG: Check role mapping
            print(f"DEBUG: Raw role from form: {raw_role}")
            print(f"DEBUG: Looking for questions with role: {raw_role}")
            created = 0
            # Safety caps
            max_attempts = max(50, n * 10)
            attempts = 0
                # DEBUG: Count how many questions were actually created
            total_questions = GeneratedQuestion.objects.filter(role=raw_role).count()
            print(f"DEBUG: Total questions for role '{raw_role}': {total_questions}")
            if total_questions == 0:
                print("DEBUG: WARNING: No questions generated! Creating fallback questions...")
                # Create emergency fallback questions
                for i in range(1, n+1):
                    GeneratedQuestion.objects.create(
                        role=raw_role,
                        difficulty=3,
                        text=f"({raw_role}) Question {i}: Describe your relevant experience and skills.",
                        keywords=f"{raw_role},experience,skills",
                        source='emergency'
                    )
            # 1) Try to get questions from Groq (llama-3.1-8b-instant)
            llm_questions = []
            try:
                # generate_questions_groq returns list of dicts: {'text','keywords','difficulty'}
                llm_questions = generate_questions_groq(role=role_for_prompt, n=n, difficulty=3, model="llama-3.1-8b-instant")
                
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
                    role=role_for_prompt,
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
                    payload = generate_question_stub(role_for_prompt, difficulty=2)  # your existing stub function
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
                    role=role_for_prompt,
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
    
    # Count how many questions have been answered in this session
    answered_count = session.answers.count()
    
    # Check if we've reached the requested number of questions
    # Default to 5 if not specified (for backward compatibility)
    requested_count = getattr(session, 'total_questions', 5)
    
    print(f"DEBUG: Answered {answered_count} questions, requested {requested_count}")
    
    if answered_count >= requested_count:
        # All requested questions answered, go to summary
        print(f"DEBUG: All {requested_count} questions answered, redirecting to summary")
        return redirect('interviewapp:session_summary', session_id=session.id)
    
    # Get used question IDs
    used_q_ids = session.answers.values_list('question_id', flat=True)
    
    # Find next question
    q = GeneratedQuestion.objects.filter(role=session.role).exclude(id__in=used_q_ids).first()
    
    if not q:
        print("DEBUG: No more questions available, going to summary")
        return redirect('interviewapp:session_summary', session_id=session.id)
    
    # Increment index and create answer
    with transaction.atomic():
        # Set current index to (answered + 1) to show correct question number
        session.current_index = answered_count + 1
        session.save()
        ans = Answer.objects.create(session=session, question=q, index=session.current_index)
    
    form = AnswerForm()
    return render(request, 'interview.html', {'question': q, 'answer_id': ans.id, 'form': form, 'session': session})

@login_required
def submit_answer(request, session_id):
    if request.method != 'POST':
        return redirect('interviewapp:next_question', session_id=session_id)
    
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    answer_id = request.POST.get('answer_id')
    
    try:
        answer = Answer.objects.get(id=answer_id, session=session)
    except Answer.DoesNotExist:
        messages.error(request, "Answer not found.")
        return redirect('interviewapp:next_question', session_id=session.id)
    
    form = AnswerForm(request.POST)
    if form.is_valid():
        answer_text = form.cleaned_data.get('answer_text', '').strip()
        
        if not answer_text:
            messages.error(request, "Please provide an answer.")
            return redirect('interviewapp:next_question', session_id=session.id)
        
        # Save the answer text
        answer.answer_text = answer_text
        
        # Get AI analysis
        try:
            result = analyze_transcript(answer_text, answer.question)
            answer.score = result['score']
            answer.feedback = result['feedback']
            answer.processed = True
        except Exception as e:
            # If analysis fails, still save answer but with default score
            answer.score = 5
            answer.feedback = f"Analysis failed: {str(e)}. Your answer was saved."
            answer.processed = False
        
        answer.save()
        
        # Show success message
        messages.success(request, "Answer submitted successfully!")
        
        # Redirect to next question
        return redirect('interviewapp:next_question', session_id=session.id)
    
    # If form invalid, show the question again
    return render(request, 'interview.html', {
        'question': answer.question,
        'answer_id': answer.id,
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
    
    answers = session.answers.select_related('question').all().order_by('index')
    scores = [a.score for a in answers if a.score is not None]
    avg = sum(scores)/len(scores) if scores else None
    session.total_score = avg
    session.save()
    
    # Calculate duration (example: using started_at and completed_at)
    duration = 0
    if session.started_at and hasattr(session, 'completed_at') and session.completed_at:
        duration = int((session.completed_at - session.started_at).total_seconds() / 60)
    
    # Generate strengths and improvements from feedback
    strengths = []
    improvements = []
    for answer in answers:
        if answer.feedback:
            # Simple parsing - adjust based on your feedback structure
            if 'good' in answer.feedback.lower() or 'excellent' in answer.feedback.lower():
                strengths.append(f"Strong answer to: {answer.question.text[:50]}...")
            if 'improve' in answer.feedback.lower() or 'better' in answer.feedback.lower():
                improvements.append(f"Could improve: {answer.question.text[:50]}...")
    
    # Remove duplicates
    strengths = list(set(strengths))[:3]
    improvements = list(set(improvements))[:3]
    
    return render(request, 'summary.html', {
        'session': session,
        'answers': answers,
        'avg': round(avg, 2) if avg else None,
        'duration': duration,
        'strengths': strengths,
        'improvements': improvements
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

@login_required
def start_session_simple(request):
    """
    Minimal working version for testing
    """
    if request.method == 'POST':
        form = SimpleStartForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            n = form.cleaned_data['n_questions']
            
            # Create session
            session = InterviewSession.objects.create(
                user=request.user,
                role=role,
                total_questions=n
            )
            
            # Create simple questions without AI
            for i in range(n):
                text = f"{role} Question {i+1}: Describe your experience with relevant technologies."
                sig = signature_of_text(text)
                
                if not GeneratedQuestion.objects.filter(signature=sig).exists():
                    GeneratedQuestion.objects.create(
                        role=role,
                        difficulty=3,
                        text=text,
                        keywords=f"{role},experience,technologies",
                        signature=sig,
                        source='manual'
                    )
            
            messages.success(request, f"Interview session started with {n} questions!")
            return redirect('interviewapp:next_question', session_id=session.id)
    else:
        form = SimpleStartForm()
    
    return render(request, 'start.html', {'form': form})