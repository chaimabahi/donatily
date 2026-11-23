from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    class Kind(models.TextChoices):
        DONATION = "donation", "Don"
        UNSOLD = "unsold", "Invendu"
        DISCOUNT = "discount", "Promotion solidaire"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PENDING = "pending", "En modération"
        APPROVED = "approved", "Publié"
        REJECTED = "rejected", "Refusé"
        ARCHIVED = "archived", "Archivé"

    class Unit(models.TextChoices):
        PIECE = "piece", "pièce"
        KG = "kg", "kg"
        LOT = "lot", "lot"
        PACK = "pack", "paquet"

    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    name = models.CharField(max_length=180)
    description = models.TextField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.PIECE)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    credit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    moderation_note = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "kind"]),
            models.Index(fields=["merchant", "status"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(stock__gte=0), name="product_stock_gte_0"),
            models.CheckConstraint(condition=models.Q(credit_cost__gte=0), name="product_credit_cost_gte_0"),
            models.CheckConstraint(condition=models.Q(original_price__gte=0), name="product_original_price_gte_0"),
            models.CheckConstraint(condition=models.Q(offer_price__gte=0), name="product_offer_price_gte_0"),
        ]

    def __str__(self):
        return self.name

    @property
    def primary_image(self):
        image = self.images.filter(is_primary=True).first() or self.images.first()
        return image


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=180, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "created_at"]

    def __str__(self):
        return self.alt_text or f"Image {self.pk}"
