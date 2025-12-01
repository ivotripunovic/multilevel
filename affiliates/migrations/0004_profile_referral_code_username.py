from django.db import migrations, models


def sync_referral_codes(apps, schema_editor):
    Profile = apps.get_model("affiliates", "Profile")

    for profile in Profile.objects.select_related("user").all():
        username = profile.user.username
        if profile.referral_code != username:
            profile.referral_code = username
            profile.save(update_fields=["referral_code"])


class Migration(migrations.Migration):

    dependencies = [
        ("affiliates", "0003_alter_commission_options_commission_approved_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="referral_code",
            field=models.CharField(editable=False, max_length=150, unique=True),
        ),
        migrations.RunPython(sync_referral_codes, migrations.RunPython.noop),
    ]
