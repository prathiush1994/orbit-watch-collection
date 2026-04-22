from .models import Category


def menu_links(request):
    links = Category.objects.filter(status="active")
    return dict(links=links)
