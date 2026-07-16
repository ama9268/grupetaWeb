from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_backfill_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['is_admin'], name='accounts_up_is_admin_idx'),
        ),
    ]
