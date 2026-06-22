from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.db.models import Count
from category.models import Category
from .decorators import admin_required
import re 


def _unique_slug(name, exclude_id=None):
    base = slugify(name)
    slug = base
    qs = Category.objects.all()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    counter = 1
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@admin_required
def category_list(request):
    search_query = request.GET.get("q", "").strip()

    categories = Category.objects.annotate(
        product_count=Count("product", distinct=True)
    ).order_by("category_name")

    if search_query:
        categories = categories.filter(category_name__icontains=search_query)

    paginator = Paginator(categories, 7)
    page = request.GET.get("page", 1)
    categories = paginator.get_page(page)

    context = {
        "categories": categories,
        "search_query": search_query,

    }
    return render(request, "adminpanel/categories.html", context)


@admin_required
def category_add(request):
    if request.method == "POST":
        name = request.POST.get("category_name", "").strip()

        if not name:
            messages.error(
                request, "Category name is required.",
            )
            return redirect("admin_category_list")
        
        if name.isdigit():
            messages.error(
                request, "Category cant be digits",
            )
            return redirect("admin_category_list")
        
        if re.match(r"^[!@#$%^&*()]$", name):
            messages.error(
                request,
                "Special characters are not allowed in category names."
            )
            return redirect("admin_category_list")

        if not re.match(r"^[A-Z][A-Za-z0-9\s_-]*$", name):
            messages.error(
                request,
                "Category must start with a capital letter."
            )
            return redirect("admin_category_list")

        if Category.objects.filter(category_name__iexact=name).exists():
            messages.error(request, f'Category "{name}" already exists.')
            return redirect("admin_category_list")

        Category.objects.create(
            category_name=name,
            slug=_unique_slug(name),
            status="active",
        )
        messages.success(request, f'Category "{name}" added successfully.')

    return redirect("admin_category_list")


@admin_required
def category_edit(request, category_id):
    cat = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get("category_name", "").strip()

        if not name:
            messages.error(request, "Category name is required.")
            return redirect("admin_category_list")
            
        if re.match(r"^[!@#$%^&*()]$", name):
            messages.error(
                request,
                "Special characters are not allowed in category names."
            )
            return redirect("admin_category_list")

        if not re.match(r"^[A-Z][A-Za-z0-9\s_-]*$", name):
            messages.error(
                request,
                "Category must start with a capital letter."
            )
            return redirect("admin_category_list")

        if (
            Category.objects.filter(category_name__iexact=name)
            .exclude(id=category_id)
            .exists()
        ):
            messages.error(request, f'Category "{name}" already exists.')
            return redirect("admin_category_list")

        cat.category_name = name
        new_slug = slugify(name)
        if new_slug != cat.slug:
            cat.slug = _unique_slug(name, exclude_id=category_id)
        cat.save()
        messages.success(request, f'Category updated to "{name}" successfully.')

    return redirect("admin_category_list")


@admin_required
@require_POST
def category_toggle(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    cat.status = "inactive" if cat.status == "active" else "active"
    cat.save()
    messages.success(
        request, f'Category "{cat.category_name}" has been {cat.status} successfully.'
    )
    return redirect("admin_category_list")


def category_suggestions(request):
    q = request.GET.get("q", "").strip()
    suggestions = []
    if len(q) >= 2:
        suggestions = list(
            Category.objects.filter(category_name__icontains=q)
            .values_list("category_name", flat=True)
            .order_by("category_name")[:8]
        )
    return JsonResponse({"suggestions": suggestions})
