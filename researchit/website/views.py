from django.views.generic import TemplateView


class MainPageView(TemplateView):
    template_name = "website/main_page.html"
