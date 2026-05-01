import qrcode
import base64
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import re
from datetime import date, datetime 
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse
from django.db import IntegrityError, transaction

from .models import courts, Booking, UserProfile
from django.contrib.admin.views.decorators import staff_member_required

# canonical slot list — keep consistent with template
SLOTS = [
    "12:00 - 13:00",
    "14:00 - 15:00",
    "17:00 - 18:00",
    "18:00 - 19:00",
    "19:00 - 20:00",
    "20:00 - 21:00",
]

# ---------------- HOME ----------------
def home(request):
    return render(request, 'pickleball/basic.html')

# ---------------- COURTS ----------------
from .models import courts

def court_list(request, game_type=None):

    # Always start with all courts
    court_list = courts.objects.all()

    # Filter by game type (pickleball / cricket)
    if game_type:
        court_list = court_list.filter(game_type=game_type)

    return render(request, 'pickleball/court_list.html', {
        'courts': court_list,
        'game_type': game_type,
    })



# ---------------- BOOKING ----------------
def book_court(request, court_id):
    court = get_object_or_404(courts, id=court_id)

    # determine selected date from GET or default to today
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    # fetch booked slots for this court & selected_date (include pending or only paid depending on business rule)
    # Here we block both pending and paid to prevent double attempts; you can change filter(status='paid') if you prefer
    booked_qs = Booking.objects.filter(court=court, date=selected_date)
    booked_slots = set(booked_qs.values_list('time_slot', flat=True))

    available_slots = [s for s in SLOTS if s not in booked_slots]

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        slot = request.POST.get('slot')
        day = request.POST.get('day')  # expected YYYY-MM-DD
        address = request.POST.get('address', '')

        # basic validation
        if not (name and email and phone and slot and day):
            messages.error(request, "Please complete all required fields.")
            return redirect(request.path + f"?date={selected_date.isoformat()}")

        # validate phone
        if not re.match(r'^[6-9]\d{9}$', phone):
            messages.error(request, "Invalid phone number. Enter 10-digit starting with 6-9.")
            return redirect(request.path + f"?date={selected_date.isoformat()}")

        try:
            booking_date = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date selected.")
            return redirect(request.path + f"?date={selected_date.isoformat()}")

        # Race-safe booking: create a pending booking inside a transaction. unique_together prevents duplicates.
        try:
            with transaction.atomic():
                new_booking = Booking.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    court=court,
                    date=booking_date,
                    time_slot=slot,
                    address=address,
                    status='pending'   # will become 'paid' after payment success
                )
        except IntegrityError:
            messages.error(request, "Sorry — that slot was just booked. Please choose another slot.")
            return redirect(request.path + f"?date={selected_date.isoformat()}")

        # store booking id in session for payment flow
        request.session['booking_id'] = new_booking.id
        request.session.set_expiry(60 * 30)  # 30 minutes
        return redirect('payment')

    return render(request, 'pickleball/book_court.html', {
        'court': court,
        'selected_date': selected_date,
        'available_slots': available_slots,
        'booked_slots': booked_slots,
        'slots': SLOTS,
    })

# ---------------- CONFIRM / PAYMENT ----------------
def payment(request):
    booking_id = request.session.get('booking_id')
    if not booking_id:
        messages.error(request, "No booking found in session. Start again.")
        return redirect('home')

    booking = Booking.objects.filter(id=booking_id).first()
    if not booking:
        messages.error(request, "Booking not found.")
        return redirect('home')

    if request.method == 'POST':
        method = (request.POST.get('method') or '').strip().lower()

        # If UPI: show QR
        if method == "upi":
            upi_id = "8866642218@ptyes"  # replace with your UPI ID
            amount = float(booking.court.price or 0)

            upi_url = f"upi://pay?pa={upi_id}&pn=BookMyCourt&am={amount}&cu=INR"

            qr = qrcode.make(upi_url)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()

            # mark payment pending in session
            request.session['payment'] = {'method': 'upi', 'status': 'pending', 'amount': amount}

            return render(request, 'pickleball/upi_payment.html', {
                'booking': booking,
                'qr_code': qr_base64,
                'upi_url': upi_url,
                'amount': amount,
                'booking_id': booking_id,
            })

        # For other methods assume success (or integrate gateway)
        request.session['payment'] = {'method': method, 'status': 'success', 'amount': float(booking.court.price or 0)}

        # finalize booking immediately
        booking.payment_method = method
        booking.status = 'paid'
        booking.save()

        # send email
        try:
            send_mail(
                subject="Booking Confirmed",
                message=(
                    f"Hi {booking.name},\n\nYour booking for {booking.court} on {booking.date} "
                    f"at {booking.time_slot} is confirmed.\nPayment method: {method}\nAmount: ₹{booking.court.price}\n"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@bookmycourt.local"),
                recipient_list=[booking.email],
                fail_silently=False,
            )
        except Exception:
            pass

        # clear session booking id
        try:
            del request.session['booking_id']
        except KeyError:
            pass

        return redirect('success')

    return render(request, 'pickleball/payment.html', {'booking': booking})

def success(request):
    # For UPI flow, the UPI page should POST here when user confirms payment was done.
    booking_id = request.session.get('booking_id')
    # If booking_id not in session, we may still be redirected after non-UPI flow
    # try to find recent paid booking by user/session (simple approach: use last paid)
    booking = None
    if booking_id:
        booking = Booking.objects.filter(id=booking_id).first()

    if request.method == 'POST':
        # user confirms UPI payment completed
        # mark booking as paid
        if booking:
            booking.payment_method = 'upi'
            booking.status = 'paid'
            booking.save()

            # send email
            try:
                send_mail(
                    subject="Booking Confirmed",
                    message=(
                        f"Hi {booking.name},\n\nYour booking for {booking.court} on {booking.date} "
                        f"at {booking.time_slot} is confirmed.\nPayment method: UPI\nAmount: ₹{booking.court.price}\n"
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@bookmycourt.local"),
                    recipient_list=[booking.email],
                    fail_silently=False,
                )
            except Exception:
                pass

        # clear booking_id
        try:
            del request.session['booking_id']
        except KeyError:
            pass

        return render(request, 'pickleball/success.html', {'booking': booking, 'method': 'upi'})

    # if GET and no payment in session, redirect to payment
    payment_info = request.session.get('payment', {})
    if not payment_info or payment_info.get('status') != 'success':
        # If the payment was non-UPI, booking was already marked paid in payment view
        # If UPI, user should confirm via POST from upi_payment.html
        return redirect('payment')

    # else try to find booking (fallback)
    if not booking:
        booking = Booking.objects.filter(status='paid').order_by('-created_at').first()

    return render(request, 'pickleball/success.html', {'booking': booking, 'method': payment_info.get('method', 'unknown')})

# ---------------- AUTH ----------------
def register(request):
    if request.method == 'POST':
        username = request.POST.get('name') or request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone')

        if not re.match(r'^[6-9]\d{9}$', phone):
            messages.error(request, "Invalid phone number! Please enter a 10-digit mobile number starting with 6–9.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('register')

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )
        user.save()

        # create profile
        try:
            UserProfile.objects.create(user=user, phone=phone)
        except Exception:
            # if profile fails (race etc), ignore but user created
            pass

        messages.success(request, "Registration successful! Please login.")
        return redirect('login')

    return render(request, 'pickleball/register.html')

def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome {user.username}!")
            return redirect("booking")
        else:
            messages.error(request, "Invalid credentials")
            return redirect("login")

    return render(request, "pickleball/login.html")

def logout(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("home")

# ---------------- BOOKING PAGE ----------------
def book_pg(request):
    return render(request, 'pickleball/booking.html')

# ---------------- ADMIN ----------------
@staff_member_required
def admin_dashboard(request):
    courts = courts.objects.all()
    bookings = Booking.objects.all().order_by("-id")

    return render(request, "pickleball/admin_dashboard.html", {
        "courts": courts,
        "bookings": bookings
    })

@staff_member_required
def toggle_court(request, court_id):
    court = get_object_or_404(courts, id=court_id)
    court.is_available = not court.is_available
    court.save()
    return redirect("admin_dashboard")

# cookie helpers (unchanged)
def set_cookie_view(request):
    response = HttpResponse("Cookie set!")
    response.set_cookie('user_name', 'Punya', max_age=300)
    return response

def get_cookie_view(request):
    name = request.COOKIES.get('user_name')
    return HttpResponse(f"Hello {name}")
@require_GET
def payment_status(request, booking_id):
    """
    Polled by client to check whether the booking with booking_id is paid.
    Returns JSON: {"status":"pending"} or {"status":"paid"}
    """
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    return JsonResponse({"status": booking.status})
