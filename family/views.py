"""The pages: each function gathers the data and fills a template."""
from django.shortcuts import render


def tree(request):
    return render(request, "family/tree.html")


def person_list(request):
    return render(request, "family/person_list.html")
