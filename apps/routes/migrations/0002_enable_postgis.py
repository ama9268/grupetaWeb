from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Activa la extensión PostGIS en la base de datos.

    Requiere que el rol de BD de `DATABASE_URL` tenga privilegio CREATE EXTENSION
    sobre la base de datos; si no lo tiene, esta migración falla con un error claro
    de Postgres y hace falta un `CREATE EXTENSION postgis;` manual una vez (ver
    despliegue.md).
    """

    dependencies = [
        ('routes', '0001_initial'),
    ]

    operations = [
        CreateExtension('postgis'),
    ]
