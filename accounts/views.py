from django.shortcuts import render, redirect
from .import forms

def signup(request):
    signup_form = forms.SignupForm(request.POST or None)
    if signup_form.is_valid():
        user = signup_form.save(commit=False)
        user.set_password(signup_form.cleaned_data['password'])
        user.save()
        return redirect('accounts:home')
    return render(
        request, 'accounts/signup.html',context= {
            'signup_form': signup_form,
            'hide_navbar': True
        }
    )