from django.shortcuts import render
from django.views.generic import TemplateView


class IndexGreenView(TemplateView):
    template_name = "about/index.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
