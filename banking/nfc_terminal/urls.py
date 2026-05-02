from django.urls import path

from . import views

app_name = "nfc_terminal"

urlpatterns = [
    path("", views.terminal_page, name="terminal"),
    path("readers/", views.readers_list, name="readers"),
    path("reader/", views.select_reader, name="reader"),
    path("charge/", views.charge, name="charge"),
    path("program/", views.program_page, name="program"),
    path("program/submit/", views.program_card, name="program_submit"),
    path("program/state/", views.program_state, name="program_state"),
    path("config/", views.config_page, name="config"),
    path("config/state/", views.config_state, name="config_state"),
    path("config/save/", views.config_save, name="config_save"),
]
