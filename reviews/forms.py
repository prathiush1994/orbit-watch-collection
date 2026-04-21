from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        widget=forms.HiddenInput(),
    )

    class Meta:
        model  = Review
        fields = ['rating', 'title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={
                'class'      : 'form-control',
                'placeholder': 'Summary (optional)',
                'maxlength'  : '120',
            }),
            'body': forms.Textarea(attrs={
                'class'      : 'form-control',
                'placeholder': 'Share your experience with this product…',
                'rows'       : 4,
                'maxlength'  : '1000',
            }),
        }
        labels = {
            'title': 'Review Title',
            'body' : 'Your Review',
        }

    def clean_rating(self):
        rating = int(self.cleaned_data['rating'])
        if not 1 <= rating <= 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating