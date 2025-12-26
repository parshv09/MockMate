# interviewapp/forms.py
from django import forms
from .models import Answer
class StartSessionForm(forms.Form):
    ROLE_CHOICES = [('tech','Tech'),('hr','HR'),('apt','Aptitude'),('beh','Behavioral')]
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    n_questions = forms.IntegerField(min_value=1, max_value=30, initial=5)

class AnswerForm(forms.Form):
        class Meta:
            model = Answer
            fields = ["answer_text", "audio_file"]
