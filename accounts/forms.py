from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()

class SignupForm(forms.ModelForm):

    confirm_password = forms.CharField(
        label='パスワード再入力', widget=forms.PasswordInput()
    )
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        labels = {
            'username': '名前',
            'email': 'メールアドレス',
            'password': 'パスワード',
        }
        widgets ={'password': forms.PasswordInput()}
    

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password !=confirm_password:
            self.add_error('confirm_password', 'パスワードが一致しません')
        if password:
            try:
                validate_password(password, self.instance)
            except ValidationError as e:
                self.add_error('password', e)
        return cleaned_data
    
    def save(self, commit=False):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user