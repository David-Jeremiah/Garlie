from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import ContactMessage, Order, Profile, Review

User = get_user_model()


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "email", "phone", "address", "city", "country", "payment_method", "notes"]
        labels = {
            "full_name": "Full name",
            "phone": "Phone (for delivery)",
            "address": "Delivery address",
            "notes": "Delivery notes (optional)",
            "payment_method": "How would you like to pay?",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "payment_method": forms.RadioSelect,
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "address": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2"}),
        }


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(5, "5"), (4, "4"), (3, "3"), (2, "2"), (1, "1")], coerce=int, widget=forms.RadioSelect
    )

    class Meta:
        model = Review
        fields = ["name", "rating", "title", "body"]
        labels = {"name": "Your name", "title": "Headline (optional)", "body": "Your review"}
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}


class NewsletterForm(forms.Form):
    email = forms.EmailField()


class TrackForm(forms.Form):
    number = forms.CharField(label="Order number", max_length=14)
    email = forms.EmailField(label="Email used at checkout")


def _email_taken(email, exclude_pk=None):
    qs = User.objects.filter(email__iexact=email) | User.objects.filter(username__iexact=email)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


class SignupForm(UserCreationForm):
    full_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(max_length=150, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    phone = forms.CharField(max_length=30, label="Phone", widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if _email_taken(email):
            raise forms.ValidationError("An account with this email already exists. Try logging in.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["full_name"]
        user.save()
        profile = user.profile
        profile.phone = self.cleaned_data["phone"]
        profile.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Email", widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))

    def clean_username(self):
        value = self.cleaned_data["username"].strip()
        return value.lower() if "@" in value else value


class ProfileForm(forms.ModelForm):
    full_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(max_length=150, widget=forms.EmailInput(attrs={"autocomplete": "email"}))

    class Meta:
        model = Profile
        fields = ["phone", "address", "city", "country", "photo"]
        labels = {"phone": "Phone", "address": "Delivery address", "photo": "Profile photo (optional)"}
        widgets = {
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "address": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2"}),
        }

    field_order = ["full_name", "email", "phone", "address", "city", "country", "photo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = self.instance.user
        self.fields["full_name"].initial = self.user.first_name
        self.fields["email"].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if _email_taken(email, exclude_pk=self.user.pk):
            raise forms.ValidationError("Another account already uses this email.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        user = self.user
        email = self.cleaned_data["email"]
        if user.username.lower() == (user.email or "").lower():
            user.username = email  # the email is also the login name
        user.email = email
        user.first_name = self.cleaned_data["full_name"]
        user.save()
        return profile
