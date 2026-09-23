# interviewapp/forms.py
from django import forms
from .models import Answer
class StartSessionForm(forms.Form):
    ROLE_CHOICES = [('tech','Tech'),('hr','HR'),('apt','Aptitude'),('beh','Behavioral')]
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    job_role = forms.CharField(
        max_length=100,
        required=True,
        initial='Software Engineer',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Python Developer, Data Analyst, Project Manager',
            'class': 'w-full px-5 py-4 bg-white/60 border border-white rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-500/20 font-bold text-slate-800'
        })
    )
    difficulty = forms.ChoiceField(
        choices=[
            ('1', 'Beginner'),
            ('3', 'Intermediate'),
            ('5', 'Advanced / Expert')
        ],
        initial='3',
        widget=forms.RadioSelect(attrs={
            'class': 'sr-only peer'
        })
    )
    n_questions = forms.IntegerField(min_value=1, max_value=30, initial=5)

class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["answer_text", "audio_file"]
