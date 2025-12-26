# interviewapp/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('job_seeker', 'Job Seeker'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')
    target_role = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"


class GeneratedQuestion(models.Model):
    ROLE_CHOICES = [('hr','HR'),('tech','Tech'),('apt','Aptitude'),('beh','Behavioral')]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='hr')
    difficulty = models.IntegerField(default=1)
    text = models.TextField()
    keywords = models.TextField(blank=True)
    source = models.CharField(max_length=50, default='llm')  # 'llm' or 'template'
    signature = models.CharField(max_length=128, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.text[:70]}"

class InterviewSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='general')
    started_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, default='in_progress')
    current_index = models.IntegerField(default=0)
    total_score = models.FloatField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_questions = models.IntegerField(default=0)  # Track total questions
    
    @property
    def answered_count(self):
        return self.answers.filter(processed=True).count()

    
    @property
    def total_questions(self):
        # ✅ total questions in this session
        return self.answers.count()

    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() / 60)
        return 0

    @property
    def is_completed(self):
        return self.total_questions > 0 and self.answered_count == self.total_questions

    def __str__(self):
        return f"Session {self.id} - {self.role}"
    
class Answer(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(GeneratedQuestion, on_delete=models.SET_NULL, null=True)
    index = models.IntegerField()
    answer_text = models.TextField(blank=True)
    audio_file = models.FileField(upload_to="voice_answers/", null=True, blank=True)
    transcript = models.TextField(blank=True)
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    improvement_tips = models.JSONField(null=True, blank=True)
    class Meta:
        unique_together = ('session','index')

class SessionQuestion(models.Model):
    """Links questions to specific sessions to prevent repeats"""
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='session_questions')
    question = models.ForeignKey(GeneratedQuestion, on_delete=models.CASCADE)
    asked = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Session {self.session.id} - Q{self.order}"