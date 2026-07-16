import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_sanitize_existing_posts'),
        ('groups', '0002_create_default_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='group',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='posts', to='groups.group',
            ),
        ),
        migrations.AddIndex(
            model_name='post',
            index=models.Index(fields=['group', '-created_at'], name='blog_post_group_created_idx'),
        ),
    ]
