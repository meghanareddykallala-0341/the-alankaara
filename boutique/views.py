from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Product, Order, OrderItem
from .ml.recommendation_service import recommend_products


# -------------------------
# HOME AND COLLECTIONS
# -------------------------

def home(request):
    products = Product.objects.filter(
        is_available=True
    ).order_by("-created_at")

    return render(
        request,
        "boutique/home.html",
        {"products": products},
    )


def anarkalis(request):
    products = Product.objects.filter(
        category="anarkalis",
        is_available=True,
    ).order_by("-created_at")

    return render(
        request,
        "boutique/anarkalis.html",
        {"products": products},
    )


def collection(request, category):
    collection_names = {
        "sarees": "Sarees",
        "lehengas": "Lehengas",
        "anarkalis": "Anarkalis",
        "kurtis": "Kurtis",
        "coord-sets": "Co-ord Sets",
        "indo-western": "Indo-Western",
        "dupattas": "Dupattas",
        "jewellery": "Jewellery",
        "footwear": "Footwear",
        "handbags": "Handbags",
    }

    if category not in collection_names:
        raise Http404("Collection not found")

    products = Product.objects.filter(
        category=category,
        is_available=True,
    ).order_by("-created_at")

    return render(
        request,
        "boutique/collection.html",
        {
            "products": products,
            "collection_title": collection_names[category],
        },
    )


def all_collections(request):
    collections = [
        ("Sarees", "sarees"),
        ("Lehengas", "lehengas"),
        ("Anarkalis", "anarkalis"),
        ("Kurtis", "kurtis"),
        ("Co-ord Sets", "coord-sets"),
        ("Indo-Western", "indo-western"),
        ("Dupattas", "dupattas"),
        ("Jewellery", "jewellery"),
        ("Footwear", "footwear"),
        ("Handbags", "handbags"),
    ]

    return render(
        request,
        "boutique/collections.html",
        {"collections": collections},
    )


def product_detail(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True,
    )

    return render(
        request,
        "boutique/product_detail.html",
        {"product": product},
    )


# -------------------------
# CART HELPERS
# -------------------------

def get_valid_size(product, submitted_size):
    available_sizes = product.available_sizes

    if not available_sizes:
        return "Free Size"

    submitted_size = (submitted_size or "").strip()

    for size in available_sizes:
        if size.casefold() == submitted_size.casefold():
            return size

    return None


def cart_key(product_id, size):
    return f"{product_id}|{size}"


def get_cart_data(request):
    cart_data = request.session.get("cart", {})
    cleaned_cart = {}
    items = []
    total = Decimal("0.00")

    for key, quantity_value in cart_data.items():
        try:
            product_id_text, submitted_size = key.split("|", 1)
            product_id = int(product_id_text)
            quantity = int(quantity_value)
        except (ValueError, TypeError, AttributeError):
            continue

        if not 1 <= quantity <= 99:
            continue

        product = Product.objects.filter(
            id=product_id,
            is_available=True,
        ).first()

        if product is None:
            continue

        size = get_valid_size(product, submitted_size)

        if size is None:
            continue

        normalized_key = cart_key(product.id, size)

        cleaned_cart[normalized_key] = min(
            cleaned_cart.get(normalized_key, 0) + quantity,
            99,
        )

    for key, quantity in cleaned_cart.items():
        product_id_text, size = key.split("|", 1)

        product = Product.objects.get(id=int(product_id_text))
        subtotal = product.price * quantity
        total += subtotal

        items.append({
            "key": key,
            "product": product,
            "size": size,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if cleaned_cart != cart_data:
        request.session["cart"] = cleaned_cart
        request.session.modified = True

    return items, total


# -------------------------
# CART ACTIONS
# -------------------------

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True,
    )

    size = get_valid_size(product, request.POST.get("size"))

    if size is None:
        return redirect("product_detail", product_id=product.id)

    key = cart_key(product.id, size)
    cart_data = request.session.get("cart", {})

    try:
        current_quantity = int(cart_data.get(key, 0))
    except (ValueError, TypeError):
        current_quantity = 0

    cart_data[key] = min(max(current_quantity, 0) + 1, 99)

    request.session["cart"] = cart_data
    request.session.modified = True

    if request.POST.get("next") == "checkout":
        return redirect("checkout")

    return redirect("cart")


def cart(request):
    items, total = get_cart_data(request)

    return render(
        request,
        "boutique/cart.html",
        {"items": items, "total": total},
    )


@require_POST
def update_cart(request, product_id):
    cart_data = request.session.get("cart", {})
    size = (request.POST.get("size") or "").strip()
    key = cart_key(product_id, size)

    if key in cart_data:
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            quantity = 1

        if quantity <= 0:
            cart_data.pop(key, None)
        else:
            cart_data[key] = min(quantity, 99)

        request.session["cart"] = cart_data
        request.session.modified = True

    return redirect("cart")


@require_POST
def remove_from_cart(request, product_id):
    cart_data = request.session.get("cart", {})
    size = (request.POST.get("size") or "").strip()
    key = cart_key(product_id, size)

    cart_data.pop(key, None)

    request.session["cart"] = cart_data
    request.session.modified = True

    return redirect("cart")


# -------------------------
# CHECKOUT
# -------------------------

def checkout(request):
    items, total = get_cart_data(request)

    if not items:
        return redirect("cart")

    fields = [
        "customer_name",
        "phone",
        "email",
        "address",
        "city",
        "state",
        "pincode",
    ]

    form_data = {field: "" for field in fields}
    errors = {}

    if request.method == "POST":
        for field in fields:
            form_data[field] = request.POST.get(field, "").strip()

        required_fields = [
            "customer_name",
            "phone",
            "address",
            "city",
            "state",
            "pincode",
        ]

        for field in required_fields:
            if not form_data[field]:
                errors[field] = "This field is required."

        if len(form_data["customer_name"]) > 150:
            errors["customer_name"] = (
                "Name must be 150 characters or fewer."
            )

        if len(form_data["phone"]) > 20:
            errors["phone"] = "Please enter a valid phone number."

        if form_data["email"] and len(form_data["email"]) > 254:
            errors["email"] = "Please enter a valid email address."

        if len(form_data["city"]) > 100:
            errors["city"] = "City must be 100 characters or fewer."

        if len(form_data["state"]) > 100:
            errors["state"] = "State must be 100 characters or fewer."

        if not (
            form_data["pincode"].isdigit()
            and len(form_data["pincode"]) == 6
        ):
            errors["pincode"] = "Enter a valid 6-digit PIN code."

        if not errors:
            try:
                with transaction.atomic():
                    items, total = get_cart_data(request)

                    if not items:
                        return redirect("cart")

                    order = Order.objects.create(
                        user=(
                            request.user
                            if request.user.is_authenticated
                            else None
                        ),
                        customer_name=form_data["customer_name"],
                        phone=form_data["phone"],
                        email=form_data["email"],
                        address=form_data["address"],
                        city=form_data["city"],
                        state=form_data["state"],
                        pincode=form_data["pincode"],
                        total_amount=total,
                    )

                    for item in items:
                        OrderItem.objects.create(
                            order=order,
                            product=item["product"],
                            size=item["size"],
                            quantity=item["quantity"],
                            price=item["product"].price,
                        )

                request.session["pending_order_id"] = order.id
                request.session.modified = True

                return redirect("payment")

            except Exception:
                errors["general"] = (
                    "We couldn't place your order. "
                    "Please try again."
                )

    return render(
        request,
        "boutique/checkout.html",
        {
            "items": items,
            "total": total,
            "form_data": form_data,
            "errors": errors,
        },
    )


# -------------------------
# DEMO PAYMENT
# -------------------------

def payment(request):
    pending_order_id = request.session.get("pending_order_id")

    if not pending_order_id:
        confirmed_order_id = request.session.get("confirmed_order_id")

        if confirmed_order_id:
            return redirect(
                "order_confirmation",
                order_id=confirmed_order_id,
            )

        return redirect("cart")

    try:
        order = Order.objects.get(id=pending_order_id)
    except Order.DoesNotExist:
        request.session.pop("pending_order_id", None)
        return redirect("cart")

    items = order.items.select_related("product").all()

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        allowed_methods = ["upi", "card", "netbanking", "cod"]

        if payment_method not in allowed_methods:
            return render(
                request,
                "boutique/payment.html",
                {
                    "order": order,
                    "items": items,
                    "error": "Please select a valid payment method.",
                },
            )

        order.payment_method = payment_method

        if payment_method == "cod":
            order.payment_status = "cod"
        else:
            order.payment_status = "demo_paid"

        order.save()

        request.session["confirmed_order_id"] = order.id
        request.session.pop("pending_order_id", None)
        request.session.pop("cart", None)

        return redirect(
            "order_confirmation",
            order_id=order.id,
        )

    return render(
        request,
        "boutique/payment.html",
        {
            "order": order,
            "items": items,
        },
    )


# -------------------------
# ORDER CONFIRMATION
# -------------------------

def order_confirmation(request, order_id):
    confirmed_order_id = request.session.get("confirmed_order_id")

    if confirmed_order_id != order_id:
        return redirect("home")

    order = get_object_or_404(Order, id=order_id)

    return render(
        request,
        "boutique/order_confirmation.html",
        {"order": order},
    )


# -------------------------
# MY ORDERS
# -------------------------

@login_required(login_url="login")
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related(
        "items__product"
    )

    return render(
        request,
        "boutique/my_orders.html",
        {"orders": orders},
    )


# -------------------------
# STYLE STUDIO
# -------------------------

def style_studio(request):
    recommendations = []
    submitted = "occasion" in request.GET
    body_type = request.GET.get("body_type", "any")

    body_type_tips = {
        "hourglass": (
            "Try outfits that highlight your preferred silhouette, "
            "such as a fitted kurti, defined-waist dress, or saree."
        ),
        "pear": (
            "Explore detailed tops, bright dupattas, or co-ord sets "
            "that you feel comfortable wearing."
        ),
        "apple": (
            "Try flowy kurtis, layered outfits, or relaxed silhouettes "
            "if you enjoy those styles."
        ),
        "rectangle": (
            "Experiment with layered looks, peplum tops, belts, "
            "or draped dupattas if you like them."
        ),
        "inverted_triangle": (
            "Explore flowy skirts, wide-leg bottoms, or softly "
            "draped outfits for variety."
        ),
        "any": (
            "Explore colours, fabrics, and silhouettes based on your "
            "occasion, comfort, and personal taste."
        ),
    }

    body_type_tip = body_type_tips.get(
        body_type, body_type_tips["any"]
    )
    recommendation_error = None

    if submitted:
        occasion = request.GET.get("occasion", "daily").strip().lower()
        style = request.GET.get("style", "any").strip().lower()
        weather = request.GET.get("weather", "Mild").strip()
        preferred_colour = request.GET.get("colour", "Any").strip()

        try:
            budget = Decimal(request.GET.get("budget", "2500"))

            if not budget.is_finite() or budget <= 0:
                budget = Decimal("2500")

        except (ValueError, TypeError, ArithmeticError):
            budget = Decimal("2500")

        occasion_categories = {
            "daily": ["kurtis", "coord-sets"],
            "college": ["kurtis", "coord-sets"],
            "office": ["kurtis", "coord-sets"],
            "festive": ["sarees", "lehengas", "anarkalis"],
            "wedding": ["lehengas", "sarees", "anarkalis"],
            "party": ["indo-western", "lehengas", "coord-sets"],
        }

        style_categories = {
            "traditional": ["sarees", "lehengas", "anarkalis"],
            "modern": ["indo-western", "coord-sets"],
            "casual": ["kurtis", "coord-sets"],
            "elegant": ["sarees", "anarkalis", "indo-western"],
            "any": [],
        }

        categories = occasion_categories.get(
            occasion, ["kurtis", "coord-sets"]
        )

        preferred_categories = style_categories.get(style, [])

        if preferred_categories:
            matching_categories = [
                category
                for category in categories
                if category in preferred_categories
            ]

            categories = matching_categories or preferred_categories

        affordable_products = Product.objects.filter(
            is_available=True,
            price__lte=budget,
        )

        category_products = affordable_products.filter(
            category__in=categories
        )

        colour_aliases = {
            "pink": ["pink", "rose", "blush", "rani"],
            "red": ["red", "crimson", "scarlet"],
            "blue": ["blue", "navy", "sky blue"],
            "green": ["green", "olive", "emerald", "mint", "sage"],
            "yellow": ["yellow", "mustard"],
            "black": ["black"],
            "white": ["white", "ivory", "cream", "off-white"],
            "maroon": ["maroon", "burgundy", "wine"],
            "mustard": ["mustard", "yellow"],
            "gold": ["gold", "golden"],
        }

        def filter_by_colour(queryset):
            if (
                not preferred_colour
                or preferred_colour.casefold() == "any"
            ):
                return queryset

            terms = colour_aliases.get(
                preferred_colour.casefold(),
                [preferred_colour.casefold()],
            )

            colour_query = models.Q()

            for term in terms:
                colour_query |= models.Q(color__icontains=term)

            return queryset.filter(colour_query)

        exact_matches = filter_by_colour(category_products)

        if exact_matches.exists():
            candidate_products = exact_matches
            recommendation_error = None

        elif category_products.exists():
            candidate_products = category_products
            recommendation_error = (
                f"No {preferred_colour} products matched all your filters. "
                "Here are alternatives in your budget."
            )

        elif affordable_products.exists():
            candidate_products = affordable_products
            recommendation_error = (
                "No products matched your selected occasion and style "
                "within budget. Here are other available options."
            )

        else:
            candidate_products = Product.objects.none()
            recommendation_error = (
                "No available products are within this budget right now. "
                "Try increasing your budget."
            )

        if candidate_products.exists():
            try:
                ml_recommendations = recommend_products(
                    products=candidate_products,
                    occasion=occasion,
                    budget=budget,
                    weather=weather,
                    preferred_style=style,
                    preferred_colour=preferred_colour,
                )

                if ml_recommendations:
                    recommendations = list(ml_recommendations[:12])
                else:
                    recommendations = list(
                        candidate_products.order_by("price", "name")[:12]
                    )

                    if not recommendation_error:
                        recommendation_error = (
                            "Showing available products because the AI "
                            "model did not find suitable recommendations."
                        )

            except Exception:
                recommendations = list(
                    candidate_products.order_by("price", "name")[:12]
                )

                if not recommendation_error:
                    recommendation_error = (
                        "AI ranking is temporarily unavailable. "
                        "Here are available products within your budget."
                    )

    return render(
        request,
        "boutique/style_studio.html",
        {
            "recommendations": recommendations,
            "submitted": submitted,
            "body_type": body_type,
            "body_type_tip": body_type_tip,
            "recommendation_error": recommendation_error,
        },
    )
