from .models import Category

def menu_links(request):
    # Only pass active categories to the navbar
    links = Category.objects.filter(status='active')
    return dict(links=links)