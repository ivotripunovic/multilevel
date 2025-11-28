from decimal import Decimal
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models import Company
from .utils import record_payment, complete_payment


def index(request):
    return render(request, "payments/index.html", {})


@require_http_methods(["POST", "GET"])
def create_payment_view(request):
    """
    Minimal view to create and immediately complete a payment (demo only).
    POST params:
      - amount (optional, default 100.00)
      - company_id (optional)
    If no company_id provided, create/get a company for the logged-in user.
    """
    if request.method == "GET":
        return render(request, "payments/create.html", {})

    amount = request.POST.get("amount", "100.00")
    company_id = request.POST.get("company_id")

    # determine company
    company = None
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            company = None

    if not company:
        # prefer a company owned by the user; otherwise create a demo company
        if request.user.is_authenticated:
            company = Company.objects.filter(owner=request.user).first()
            if not company:
                company = Company.objects.create(name=f"{request.user.username}-company", owner=request.user)
        else:
            # fallback company for anonymous (single-site demo)
            company, _ = Company.objects.get_or_create(name="Default Company")

    p = record_payment(company=company, amount=Decimal(amount), payer=request.user if request.user.is_authenticated else None, fee=Decimal("0.00"))
    complete_payment(p)

    messages.success(request, f"Simulated payment of ${amount} for company {company.name} recorded.")
    return redirect("accounts-profile")