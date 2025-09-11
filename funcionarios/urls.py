# funcionarios/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "funcionarios"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("home/", views.home_view, name="home"),
    path("logout/", views.logout_view, name="logout"),
    # --- URL DE TROCA DE SENHA ATUALIZADA ---
    path(
        "password_change/",
        # Agora usando a NOSSA view customizada
        views.CustomPasswordChangeView.as_view(
            template_name="registration/password_change_form.html", success_url="done/"
        ),
        name="password_change",
    ),
    path(
        "password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
    path("bate-ponto/", views.bate_ponto_view, name="bate_ponto"),
    path(
        "supervisor/dashboard/",
        views.supervisor_dashboard_view,
        name="supervisor_dashboard",
    ),
    path("supervisor/tabela-equipe/", views.tabela_equipe_view, name="tabela_equipe"),
]
