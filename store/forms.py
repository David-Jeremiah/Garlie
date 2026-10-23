from django import forms

from .models import ContactMessage, Order, Review


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
