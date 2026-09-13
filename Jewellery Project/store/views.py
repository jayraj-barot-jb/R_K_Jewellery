import django
try:
    import razorpay
except ImportError:
    razorpay = None
from django.contrib.auth.models import User
from store.models import Address, Cart, Category, Order, Product, Payment
from django.shortcuts import redirect, render, get_object_or_404
from .forms import RegistrationForm, AddressForm
from django.contrib import messages
from django.views import View
import decimal
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator # for Class Based Views


# Create your views here.

def home(request):
    categories = Category.objects.filter(is_active=True, is_featured=True)[:3]
    products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'store/index.html', context)


def detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.exclude(id=product.id).filter(is_active=True, category=product.category)
    context = {
        'product': product,
        'related_products': related_products,

    }
    return render(request, 'store/detail.html', context)


def all_categories(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, 'store/categories.html', {'categories':categories})


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(is_active=True, category=category)
    categories = Category.objects.filter(is_active=True)
    context = {
        'category': category,
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/category_products.html', context)


# Authentication Starts Here

class RegistrationView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'account/register.html', {'form': form})
    
    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            messages.success(request, "Congratulations! Registration Successful!")
            form.save()
        return render(request, 'account/register.html', {'form': form})
        

@login_required
def profile(request):
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)
    return render(request, 'account/profile.html', {'addresses':addresses, 'orders':orders})


@method_decorator(login_required, name='dispatch')
class AddressView(View):
    def get(self, request):
        form = AddressForm()
        return render(request, 'account/add_address.html', {'form': form})

    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():
            user=request.user
            locality = form.cleaned_data['locality']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            reg = Address(user=user, locality=locality, city=city, state=state)
            reg.save()
            messages.success(request, "New Address Added Successfully.")
        return redirect('store:profile')


@login_required
def remove_address(request, id):
    a = get_object_or_404(Address, user=request.user, id=id)
    a.delete()
    messages.success(request, "Address removed.")
    return redirect('store:profile')

def logout_view(request):
    logout(request)
    return redirect('store:login')


@login_required
def add_to_cart(request):
    user = request.user
    product_id = request.POST.get('prod_id') or request.GET.get('prod_id')
    if not product_id:
        messages.error(request, "Product not specified.")
        return redirect('store:home')
    product = get_object_or_404(Product, id=product_id)

    # Check whether the Product is already in Cart or Not
    cp = Cart.objects.filter(product=product, user=user).first()
    if cp:
        cp.quantity += 1
        cp.save()
    else:
        Cart.objects.create(user=user, product=product)
    
    return redirect('store:cart')


@login_required
def cart(request):
    user = request.user
    cart_products = Cart.objects.filter(user=user)

    # Display Total on Cart Page
    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(10)
    for p in cart_products:
        amount += (p.quantity * p.product.price)

    # Customer Addresses
    addresses = Address.objects.filter(user=user)

    context = {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': amount + shipping_amount,
        'addresses': addresses,
    }
    return render(request, 'store/cart.html', context)


@login_required
def remove_cart(request, cart_id):
    c = get_object_or_404(Cart, id=cart_id, user=request.user)
    c.delete()
    messages.success(request, "Product removed from Cart.")
    return redirect('store:cart')


@login_required
def plus_cart(request, cart_id):
    cp = get_object_or_404(Cart, id=cart_id, user=request.user)
    cp.quantity += 1
    cp.save()
    return redirect('store:cart')


@login_required
def minus_cart(request, cart_id):
    cp = get_object_or_404(Cart, id=cart_id, user=request.user)
    # Remove the Product if the quantity is already 1
    if cp.quantity <= 1:
        cp.delete()
    else:
        cp.quantity -= 1
        cp.save()
    return redirect('store:cart')


@login_required
def checkout(request):
    user = request.user
    address_id = request.POST.get('address') or request.GET.get('address')
    if not address_id:
        messages.error(request, "No address selected. Please choose a shipping address before checkout.")
        return redirect('store:cart')

    # Ensure the selected address belongs to current user
    try:
        address = Address.objects.get(id=address_id, user=user)
    except Address.DoesNotExist:
        messages.error(request, "Selected address was not found. Please select a valid address.")
        return redirect('store:cart')

    # Get all the products of User in Cart
    cart = Cart.objects.filter(user=user)
    if not cart.exists():
        messages.error(request, "Your cart is empty. Add products before checkout.")
        return redirect('store:cart')

    for c in cart:
        # Saving all the products from Cart to Order
        Order(user=user, address=address, product=c.product, quantity=c.quantity).save()
        # And Deleting from Cart
        c.delete()
    messages.success(request, "Order placed successfully.")
    return redirect('store:orders')


@login_required
def orders(request):
    all_orders = Order.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'store/orders.html', {'orders': all_orders})


def shop(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    context = {
        'category': {'title': 'All Products'},
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/category_products.html', context)


def test(request):
    return render(request, 'store/test.html')


def pay(request): 
    error_message = None        
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        modelselection = request.POST.get('modelselection')
        amount = request.POST.get('amount')
        if razorpay is None:
            return render(request, 'book.html', {'error_message': 'Razorpay library is not installed in the active Python environment.'})

        client = razorpay.Client(
            auth=('rzp_test_VQhEfe2NCXbbwI', '2ibreCYL78DA3kjOhobCvz0f'))

        try:
            razorpay_payment = client.order.create(
                dict(amount=(int(amount)*100), currency='INR'))

            order_id = razorpay_payment['id']

            Payment.objects.create(
                name=name,
                phone=phone,
                email=email,
                modelselection=modelselection,
                amount=amount,
                message=message,
                order_id=order_id
            )
            razorpay_payment['name'] = name
            razorpay_payment['amount'] = amount 
            razorpay_payment['order_id'] = order_id
            return render(request, 'book.html', {'razorpay_payment': razorpay_payment})
        except Exception as e:
            error_message = str(e)
            print(f"Payment error: {error_message}")
    return render(request, 'book.html', {'error_message': error_message})


def success(request):
    status = False
    if request.method == 'POST':
        response = request.POST
        params_dict = {
            'razorpay_order_id': response.get('razorpay_order_id', ''),
            'razorpay_payment_id': response.get('razorpay_payment_id', ''),
            'razorpay_signature': response.get('razorpay_signature', ''),
        }

        client = razorpay.Client(
            auth=('rzp_test_VQhEfe2NCXbbwI', '2ibreCYL78DA3kjOhobCvz0f'))

        try:
            client.utility.verify_payment_signature(params_dict)
            status = True
            order_id = response.get('razorpay_order_id')
            if order_id:
                try:
                    razorpay_save = Payment.objects.get(order_id=order_id)
                    razorpay_save.razorpay_payment_id = response.get('razorpay_payment_id', '')
                    razorpay_save.paid = True
                    razorpay_save.save()
                except Payment.DoesNotExist:
                    pass

            if request.user.is_authenticated:
                cart_items = Cart.objects.filter(user=request.user)
                address_id = response.get('address')
                address = None
                if address_id:
                    address = Address.objects.filter(id=address_id, user=request.user).first()
                if not address:
                    address = Address.objects.filter(user=request.user).first()

                if address and cart_items.exists():
                    for c in cart_items:
                        Order.objects.create(user=request.user, address=address, product=c.product, quantity=c.quantity)
                        c.delete()
        except Exception as e:
            print(f"Payment verification error: {str(e)}")
            status = False
    return render(request, 'store/success.html', {'status': status})