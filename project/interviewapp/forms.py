# interviewapp/forms.py
from django import forms

class StartSessionForm(forms.Form):
    ROLE_CHOICES = [('tech','Tech'),('hr','HR'),('apt','Aptitude'),('beh','Behavioral')]
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    n_questions = forms.IntegerField(min_value=1, max_value=30, initial=5)

class AnswerForm(forms.Form):
    answer_text = forms.CharField(widget=forms.Textarea(attrs={'rows':4}), required=False)
