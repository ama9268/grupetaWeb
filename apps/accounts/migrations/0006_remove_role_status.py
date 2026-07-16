from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_backfill_memberships'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='userprofile',
            name='accounts_us_status_aa9625_idx',
        ),
        migrations.RemoveIndex(
            model_name='userprofile',
            name='accounts_us_role_e16858_idx',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='role',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='status',
        ),
    ]
