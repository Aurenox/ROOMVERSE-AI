from django.urls import path

from cases import api

urlpatterns = [
    path("api/", api.index),
    path("api/start/", api.start),
    path("api/games/<uuid:pk>/", api.game_detail),
    path("api/games/<uuid:pk>/answer/", api.answer),
    path("api/games/<uuid:pk>/nova/", api.nova),
    path("api/scans/", api.scan_create),
    path("api/scans/<uuid:pk>/", api.scan_detail),
    path("api/leaderboard/", api.leaderboard),
    path("api/account/<str:action>/", api.account),
]
