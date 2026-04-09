from django.urls import path

from researchit.website import views

app_name = "website"
urlpatterns = [
    path(
        "",
        views.MainPageView.as_view(),
        name="main_page",
    ),
]
