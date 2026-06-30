# Guía de despliegue — Tension en VPS con Dokploy y Traefik

Esta guía recoge exactamente lo que hay que configurar para que la app funcione en producción con Docker gestionado por Dokploy y Traefik como proxy inverso con SSL automático.

---

## Arquitectura final

```
Internet (HTTPS)
      │
   Traefik          ← gestiona el certificado SSL (Let's Encrypt)
      │                y redirige HTTP → HTTPS
      │ HTTP interno
      ▼
  Gunicorn :8080    ← sirve Django + archivos estáticos (WhiteNoise)
      │
      ▼
 PostgreSQL :5432   ← base de datos interna del stack
```

> **Sin Nginx.** Traefik hace de proxy inverso. WhiteNoise sirve los estáticos directamente desde Gunicorn. Meter Nginx entre Traefik y Django rompía las cabeceras HTTPS y causaba el error "conexión no privada".

---

## 1. Variables de entorno en Dokploy

Configura estas variables en la sección **Environment** de tu servicio en Dokploy. No uses un archivo `.env` en el servidor; Dokploy las inyecta directamente en el contenedor.

| Variable | Valor de ejemplo | Obligatoria |
|----------|-----------------|-------------|
| `SECRET_KEY` | cadena aleatoria de 64 chars | ✅ |
| `DEBUG` | `False` | ✅ |
| `ALLOWED_HOSTS` | `tension.tudominio.com,localhost,127.0.0.1` | ✅ |
| `CSRF_TRUSTED_ORIGINS` | `https://tension.tudominio.com` | ✅ |
| `DATABASE_URL` | `postgresql://tension_user:PASSWORD@db:5432/tension` | ✅ |
| `DB_PASSWORD` | contraseña segura | ✅ |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | ✅ |
| `GUNICORN_WORKERS` | `3` | opcional |
| `RUN_MIGRATIONS` | `false` (ver sección 4) | opcional |

### Por qué `localhost` en `ALLOWED_HOSTS`

El healthcheck del contenedor hace `curl http://localhost:8080/health/`. Si `localhost` no está en `ALLOWED_HOSTS`, Django responde 400 → el contenedor se marca como *unhealthy* → Traefik deja de enrutarle tráfico → **502 Bad Gateway**.

### Por qué `CSRF_TRUSTED_ORIGINS`

Con HTTPS gestionado por Traefik, Django recibe las peticiones como HTTP interno. Sin esta variable, los formularios POST (login, logout, lecturas) fallan con 403 Forbidden.

---

## 2. Configuración de Traefik en Dokploy

Dokploy genera la configuración de Traefik automáticamente. Lo único que debes verificar en la interfaz de Dokploy:

- **Puerto del contenedor**: `8080` (Gunicorn escucha en el 8080, no en el 8000)
- **Dominio**: `tension.tudominio.com`
- **SSL**: activado con `certResolver: letsencrypt`
- **Redirección HTTP → HTTPS**: activada (middleware `redirect-to-https`)

La configuración resultante de Traefik debe apuntar a `http://tension-...:8080`.

---

## 3. Primer despliegue

### 3.1 Conectar el repositorio en Dokploy

1. Crear un nuevo servicio en Dokploy → **Docker Compose**
2. Conectar con el repositorio de GitHub
3. Dokploy detecta el `docker-compose.yml` automáticamente
4. Configurar las variables de entorno (sección 1)
5. Configurar el dominio y activar SSL

### 3.2 Crear la base de datos e inicializar

En el primer despliegue hay que aplicar las migraciones y crear el superusuario. Antes de hacer el deploy, añade temporalmente en las variables de entorno:

```
RUN_MIGRATIONS=true
```

Haz **Deploy**. El contenedor aplicará las migraciones al arrancar.

Cuando el contenedor esté en marcha, ejecuta desde Dokploy → **Console** (o SSH al VPS):

```bash
docker compose exec web python manage.py createsuperuser
```

Una vez creado el superusuario, vuelve a cambiar `RUN_MIGRATIONS=false` (o elimina la variable) y haz un nuevo deploy.

---

## 4. Despliegues sucesivos (flujo normal)

El repositorio está configurado con **auto-deploy**: cada push a `main` dispara un redeploy automático en Dokploy.

### Cambios de código sin cambios en modelos

```bash
git add .
git commit -m "descripción del cambio"
git push origin main
```

Dokploy reconstruye la imagen y reinicia el contenedor. No hace falta tocar nada más.

### Cambios en modelos (nuevas migraciones)

Cuando añades un campo, modelo nuevo o cambias la estructura de la BD:

1. Genera la migración en local:
   ```bash
   python manage.py makemigrations
   ```
2. Haz commit e incluye el archivo de migración:
   ```bash
   git add apps/.../migrations/
   git commit -m "feat: ..."
   git push origin main
   ```
3. **Antes del deploy**, activa las migraciones en las variables de entorno de Dokploy:
   ```
   RUN_MIGRATIONS=true
   ```
4. Haz **Deploy** (o espera el auto-deploy)
5. Una vez desplegado, vuelve a poner `RUN_MIGRATIONS=false`

> El entrypoint aplica `python manage.py migrate` al arrancar el contenedor solo si `RUN_MIGRATIONS=true`. Así las migraciones no se ejecutan en cada deploy innecesariamente.

---

## 5. Operaciones habituales

### Ver logs en tiempo real

Desde Dokploy → **Logs** del servicio, o desde el VPS:

```bash
docker compose logs -f web
```

### Reiniciar solo la app

```bash
docker compose restart web
```

### Abrir una consola Django

```bash
docker compose exec web python manage.py shell
```

### Crear un superusuario adicional

```bash
docker compose exec web python manage.py createsuperuser
```

### Forzar reconstrucción de imagen

Desde Dokploy → **Deploy** con la opción *Force rebuild*, o desde el VPS:

```bash
docker compose up -d --build web
```

---

## 6. Solución de problemas frecuentes

| Síntoma | Causa | Solución |
|---------|-------|----------|
| **502 Bad Gateway** | El contenedor no pasa el healthcheck | Ver logs: `docker compose logs web`. Lo más habitual es que falte una variable de entorno o que `localhost` no esté en `ALLOWED_HOSTS` |
| **400 Bad Request** | El dominio no está en `ALLOWED_HOSTS` | Añadir `tension.tudominio.com` a `ALLOWED_HOSTS` en Dokploy |
| **403 Forbidden** en formularios | Falta `CSRF_TRUSTED_ORIGINS` | Añadir `https://tension.tudominio.com` a `CSRF_TRUSTED_ORIGINS` |
| **Conexión no privada** (HTTPS roto) | Certificado Let's Encrypt no emitido | Reiniciar el contenedor de Traefik: `docker restart $(docker ps -q -f name=traefik)` |
| **Archivos estáticos no cargan** | Error en `collectstatic` | Ver logs del arranque; WhiteNoise sirve los estáticos automáticamente desde Gunicorn |
| **La sesión no se mantiene** | Falta `SESSION_COOKIE_SECURE` o cookies no llegan | Verificar que `CSRF_TRUSTED_ORIGINS` incluye `https://` |

---

## 7. Qué NO hay que hacer

- ❌ **No añadir Nginx** al `docker-compose.yml`. Traefik ya hace de proxy inverso. Nginx entre Traefik y Django rompe la cabecera `X-Forwarded-Proto` y hace que Django no reconozca las conexiones como HTTPS.
- ❌ **No exponer el puerto de PostgreSQL** al host (sin `ports:` en el servicio `db`). Solo Gunicorn necesita acceder a la BD, y lo hace por la red interna de Docker.
- ❌ **No commitear el `.env`**. Las credenciales van en las variables de entorno de Dokploy.
- ❌ **No usar `STATICFILES_STORAGE`** (deprecado en Django 4.2+). Usar `STORAGES` en `settings/base.py`.
