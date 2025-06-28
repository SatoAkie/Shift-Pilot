from django.shortcuts import render, redirect ,get_object_or_404
from .import forms
from .models import Role, Invitation
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model
import uuid
from django.urls import reverse
from django.contrib import messages
from django.urls import reverse_lazy

from django.contrib.auth.views import PasswordChangeView

User = get_user_model()

def signup(request):
    signup_form = forms.SignupForm(request.POST or None)
    if signup_form.is_valid():
        user = signup_form.save(commit=False)
        user.set_password(signup_form.cleaned_data['password'])
        user.is_active = True 
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
        invitation = Invitation.objects.create(
            team=request.user.team,
            invited_by=request.user,
        )
        invite_url = request.build_absolute_uri(
            reverse('accounts:invite_register') + f'?token={invitation.token}'
        )
    else:
        invite_url = None
    return render(request, 'accounts/user_invite.html', context={'invite_url': invite_url})

def invite_register_view(request):
    token_str =  request.GET.get('token')
    invitation = get_object_or_404(Invitation, token=token_str)

    if invitation.is_used:
        return HttpResponseForbidden("この招待リンクはすでに使用されています")
    
    form = forms.SignupForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.team = invitation.team
        user.is_active = True
        user.save()
        invitation.is_used = True
        invitation.save()
        login(request, user)
        return redirect('shifts:home')
    return render(request, 'accounts/signup.html', {
        'signup_form': form,
        'hide_navbar': True
        })

@login_required#デバッグ用の記述あり、あとで削除
def mypage(request):
    if request.method == 'POST':
        print("POSTされたFILES:", request.FILES)
        form = forms.ProfileImageForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            print("画像フォームバリデーション成功")
            form.save()
            return redirect('accounts:mypage')
        else:
            print("フォームエラー:", form.errors)
    else:
        form = forms.ProfileImageForm(instance=request.user)
    return render(
        request, 'accounts/mypage.html', {
            'user': request.user,
            'form' : form,
    })
        
class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('shifts:home')

    def form_valid(self, form):
        messages.success(self.request, 'パスワードを変更しました')
        return super().form_valid(form)
    
@login_required
def user_update_view(request):
    if request.method == 'POST':
        form =forms.UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('accounts:user_update')
    else:
        form = forms.UserUpdateForm(instance=request.user)
    return render(
        request, 'accounts/user_update.html' ,{
            'user': request.user,
            'form': form,
        }
    )
