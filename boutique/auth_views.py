
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .forms import RegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "Welcome to THE ALANKAARA! Your account is ready."
            )
            return redirect("home")
    else:
        form = RegistrationForm()

    return render(
        request,
        "boutique/register.html",
        {"form": form},
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = AuthenticationForm(
            request,
            data=request.POST,
        )

        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "You are now logged in.")
            return redirect("home")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "boutique/login.html",
        {"form": form},
    )


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")
