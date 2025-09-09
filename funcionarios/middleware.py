# funcionarios/middleware.py
from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # URLs que o usuário sempre pode acessar
        allowed_paths = [
            reverse("funcionarios:password_change"),
            reverse("funcionarios:logout"),
            reverse("admin:logout"),  # Para o admin não ser afetado
        ]

        # A lógica só se aplica se o usuário estiver logado e não for um superusuário
        if request.user.is_authenticated and not request.user.is_superuser:
            # Verifica se o funcionário tem a "bandeira" e não está em uma página permitida
            if (
                request.user.funcionario.deve_alterar_senha
                and request.path not in allowed_paths
            ):
                return redirect("funcionarios:password_change")

        return response
