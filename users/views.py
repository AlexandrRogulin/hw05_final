from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.core.mail import send_mail

from .forms import CreationForm


class SignUp(CreateView):
    form_class = CreationForm
    success_url = "/auth/login/"
    template_name = "signup.html"

    send_mail(
        'Регистрация',
        'Вы успешно прошли регистрацию на сайте',
        'from@example.com',  # Это поле От:
        ['to@example.com'],  # Это поле Кому:
        fail_silently=False,
    )
