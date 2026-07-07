from django.db import migrations

from apps.blog.sanitize import sanitize_html


def sanitize_existing_posts(apps, schema_editor):
    Post = apps.get_model('blog', 'Post')
    for post in Post.objects.all():
        cleaned = sanitize_html(post.content)
        if cleaned != post.content:
            post.content = cleaned
            post.save(update_fields=['content'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(sanitize_existing_posts, migrations.RunPython.noop),
    ]
