from django.conf import settings
from django.db import models


class Distribution(models.Model):
    association = models.ForeignKey("associations.Association", on_delete=models.CASCADE, related_name="distributions")
    beneficiary = models.ForeignKey("beneficiaries.Beneficiary", on_delete=models.PROTECT, related_name="distributions")
    title = models.CharField(max_length=180)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20, default="piece")
    distributed_on = models.DateField()
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="recorded_distributions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-distributed_on", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="distribution_quantity_gt_0"),
        ]

    def __str__(self):
        return self.title
