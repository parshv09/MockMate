# interviewapp/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

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

class Answer(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(GeneratedQuestion, on_delete=models.SET_NULL, null=True)
    index = models.IntegerField()
    answer_text = models.TextField(blank=True)
    transcript = models.TextField(blank=True)
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session','index')
