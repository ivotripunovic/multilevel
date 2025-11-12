from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Company
from .utils import record_payment, complete_payment


def index(request):
    return render(request, "payments/index.html", {})


@require_POST
def create_payment_view(request):
    """
    Minimal view to create and immediately complete a payment (demo only).
    Expects: company_id, amount
    """
    company = get_object_or_404(Company, id=request.POST.get("company_id"))
    amount = Decimal(request.POST.get("amount", "0"))
    p = record_payment(company=company, amount=amount, payer=request.user if request.user.is_authenticated else None)
    complete_payment(p)
    return redirect("payments-index")