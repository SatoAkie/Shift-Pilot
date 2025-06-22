from django.shortcuts import render, redirect ,get_object_or_404
from .import forms
from .models import Role
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

def signup(request):
    signup_form = forms.SignupForm(request.POST or None)
    if signup_form.is_valid():
        user = signup_form.save(commit=False)
        user.set_password(signup_form.cleaned_data['password'])
        user.save()
        return redirect('shifts:home')
    return render(
        request, 'accounts/signup.html',context= {
            'signup_form': signup_form,
            'hide_navbar': True
        }
    )

def user_login(request):
    login_form = forms.LoginForm(request.POST or None)
    if login_form.is_valid():
        email = login_form.cleaned_data['email']
        password = login_form.cleaned_data['password']
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('shifts:home')
        else:
            return redirect('accounts:login')
    return render(
        request, 'accounts/user_login.html', context={
            'login_form': login_form,
            'hide_navbar': True
        }
    )

@login_required
def user_logout(request):
    logout(request)
    return redirect('accounts:login') 

@login_required
def user_manage_view(request):
    if not request.user.role or request.user.role.role_name != '管理者':
        return HttpResponseForbidden("このページにはアクセスできません")
    team_users = User.objects.filter(team=request.user.team)
    roles = Role.objects.all()
    context = {
        'team_users': team_users,
        'roles': roles,
    }
    return render(request, 'accounts/user_manage.html', context)

@login_required
def user_delete_view(request,user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return redirect('accounts:user_manage')
    else:
        return HttpResponseForbidden("不正なアクセスです")
    
@login_required
def user_role_update_view(request,user_id):
    if request.method == 'POST':
        role_id = request.POST.get('role_id')
        user = get_object_or_404(User, id=user_id)
        role = get_object_or_404(Role, id=role_id)
        user.role = role
        user.save()
        return redirect('accounts:user_manage')
    else:
        return HttpResponseForbidden("不正なアクセスです")
    
@login_required
def user_invite(request):
    if request.method == 'POST':
        invite_url = request.build_absolute_uri('accounts/signup/?token=csrftoken')
    else:
        invite_url = None
    return render(request, 'accounts/invite.html', context={'invite_url': invite_url})