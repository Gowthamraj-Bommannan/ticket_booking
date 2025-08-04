from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Role, StaffRequest

User = get_user_model()


@receiver(post_migrate)
def create_roles_and_superuser(sender, **kwargs):
    """
    Create default roles and superuser after migration.
    """
    if sender.name == "accounts":
        # Create roles
        roles_data = [
            {"name": "admin", "description": "System administrator with full access"},
            {"name": "user", "description": "Regular user with basic access"},
            {
                "name": "station_master",
                "description": "Station master with station management access",
            },
        ]

        for role_data in roles_data:
            Role.objects.get_or_create(
                name=role_data["name"],
                defaults={"description": role_data["description"]},
            )

        # Create superuser if it doesn't exist
        if not User.objects.filter(role="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@booking.com",
                password="admin123",
                mobile_number="9999999999",
                first_name="Admin",
                last_name="User",
                role="admin",
            )
            print("Superuser 'admin' created successfully.")


@receiver(post_save, sender=User)
def create_staff_request(sender, instance, created, **kwargs):
    """
    Create staff request when a station master is registered.
    """
    if created and instance.role == "station_master":
        StaffRequest.objects.create(user=instance)
        print(f"Staff request created for {instance.username}")


@receiver(post_save, sender=StaffRequest)
def handle_staff_request_status_change(sender, instance, **kwargs):
    """
    Handle staff request status changes and update user accordingly.
    """
    if instance.status == "approved":
        instance.user.is_active = True
        instance.user.save()
        print(f"Staff request approved for {instance.user.username}")
    elif instance.status == "rejected":
        instance.user.is_active = False
        instance.user.save()
        print(f"Staff request rejected for {instance.user.username}")
