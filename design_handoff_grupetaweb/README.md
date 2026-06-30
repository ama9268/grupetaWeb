# Handoff de diseño — GrupetaWeb · 6el1

> **Nota importante para el desarrollador:**  
> Los archivos HTML incluidos en este paquete son **prototipos de referencia visual** creados con fines de diseño, no código de producción que deba copiarse directamente. Tu tarea es **recrear estas pantallas en tu proyecto Django** usando sus plantillas, vistas, modelos y librerías habituales, siguiendo las especificaciones de este documento.

---

## Descripción general

**GrupetaWeb** es una web privada para una grupeta ciclista de carretera de ~50 miembros, apodada internamente **"6el1"**. Requiere autenticación; los nuevos registros quedan pendientes hasta que un admin o moderador los apruebe. El sistema tiene roles: **Miembro**, **Moderador**, **Admin**.

**Fidelidad:** Alta fidelidad (hifi). Los diseños incluyen colores, tipografías, espaciados e interacciones definitivos. El desarrollador debe replicarlos con fidelidad pixel a pixel usando el sistema de diseño definido en este documento.

---

## Sistema de diseño

### Paleta de colores

```
/* Modo oscuro (por defecto) */
--bg:           #100e0b   /* fondo de página */
--surface:      #1b1813   /* tarjetas, paneles, sidebar */
--surface2:     #241f17   /* inputs, avatares, hover */
--border:       #332c20   /* bordes de todos los elementos */
--text:         #f3f4f6   /* texto principal */
--dim:          #a59885   /* texto secundario, placeholders */
--accent:       #f2a93c   /* ámbar: botones primarios, badges, acento */
--ac-text:      #2a1d05   /* texto sobre fondo ámbar */
--accent-soft:  rgba(242,169,60,.16)  /* fondo suave ámbar (chips, alerts) */

/* Modo claro */
--bg:           #f7f3ec
--surface:      #ffffff
--surface2:     #f1ebe0
--border:       #e8e0d2
--text:         #15171b
--dim:          #867a66
--accent:       #e0921f   /* ámbar más oscuro para contraste */
--ac-text:      #2a1d05
--accent-soft:  rgba(224,146,31,.14)
```

**Color de estado:**
- Online / activo: `#34c759` (verde sistema)
- Pendiente / advertencia: `var(--accent)` ámbar
- Error / rechazo: `#ff453a`

### Tipografía

| Uso | Familia | Peso | Tamaño |
|-----|---------|------|--------|
| Títulos grandes, nombre de grupeta, números destacados | `Bricolage Grotesque` | 800 | 28–42px |
| Subtítulos de sección | `Bricolage Grotesque` | 800 | 17–24px |
| Body, labels, UI general | `Hanken Grotesk` | 400–700 | 12–16px |
| Números de datos, código, timestamps, monoespaciado | `IBM Plex Mono` | 400–600 | 10–14px |

Carga desde Google Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=Bricolage+Grotesque:opsz,wght@12..96,400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

### Espaciado y bordes

```
Border-radius tarjetas grandes:  16–18px
Border-radius tarjetas pequeñas: 12–14px
Border-radius avatares:          50% (círculo)
Border-radius botones primarios: 12–14px
Border-radius pills / chips:     20px (pill)
Border-radius inputs:            11px

Padding tarjeta escritorio:      14–20px
Padding tarjeta móvil:           12–16px
Gap entre tarjetas:              12–18px (desktop), 10–13px (mobile)
```

### Sombras

```
Modo oscuro:  box-shadow: 0 16px 40px rgba(0,0,0,.5)
Modo claro:   box-shadow: 0 16px 40px rgba(120,90,40,.12)
```

---

## Arquitectura Django recomendada

```
grupetaweb/
├── apps/
│   ├── accounts/       # login, registro, aprobación
│   ├── dashboard/      # vista principal
│   ├── rutas/          # subida GPX, detalle, mapa Leaflet
│   ├── eventos/        # CRUD eventos, RSVP
│   ├── galeria/        # álbumes, fotos
│   ├── blog/           # posts, comentarios, likes
│   ├── chat/           # sala general (Django Channels / polling)
│   └── miembros/       # directorio, perfil, roles
├── templates/
│   ├── base.html       # shell: topbar + bottombar + JS global
│   ├── accounts/
│   │   ├── login.html
│   │   └── register.html
│   ├── dashboard/
│   │   └── index.html
│   ├── rutas/
│   │   ├── list.html
│   │   └── detail.html
│   ├── eventos/
│   │   ├── list.html
│   │   └── detail.html
│   ├── galeria/
│   │   ├── index.html
│   │   └── album.html
│   ├── blog/
│   │   ├── list.html
│   │   └── post.html
│   ├── chat/
│   │   └── sala.html
│   └── miembros/
│       ├── list.html
│       ├── perfil.html
│       └── moderacion.html
└── static/
    ├── css/
    │   └── main.css    # variables CSS + resets
    └── js/
        └── theme.js    # lógica claro/oscuro
```

---

## `base.html` — Shell global

El shell tiene tres zonas:

### 1. Barra superior (topbar)

```
Altura: 56px en escritorio, 48px en móvil
Background: var(--surface)
Border-bottom: 1px solid var(--border)
Posición: sticky top:0; z-index:60

Contenido (escritorio, de izquierda a derecha):
  - Logo "6el1" (Bricolage Grotesque 800 22px) + claim "· la grupeta de carretera" (Hanken 500 12px, --dim)
  - Nav central: Inicio / Rutas / Eventos / Galería / Blog / Chat / Miembros
    * Item activo: fondo var(--accent), color var(--ac-text), border-radius 20px, padding 7px 13px
    * Item inactivo: color var(--dim), sin fondo
  - Derecha: indicador "N en línea" (dot verde #34c759 + Hanken 600 12px --dim, bg:--bg, border:--border, border-radius 20px) + avatar usuario (36px círculo)

Contenido (móvil):
  - Solo logo "6el1" a la izquierda y avatar a la derecha
  - La navegación pasa a la barra inferior
```

### 2. Barra inferior (bottombar) — solo móvil

```
Altura: auto (aprox. 56px con padding-bottom safe-area)
Background: var(--surface)
Border-top: 1px solid var(--border)
Posición: sticky bottom:0

5 ítems: Inicio / Rutas / Galería / Chat / Peña
  * Activo: color var(--accent) + dot ámbar sobre el label
  * Inactivo: color var(--dim) + dot --dim
  * Tipografía: Hanken 600 10px
```

### 3. Contenido principal

```
<main> con max-width:1080px, margin:0 auto, padding:24px 22px 40px
```

### Theme toggle (claro/oscuro)

Almacenar en `localStorage` con clave `g6_theme` (`"1"` = oscuro, `"0"` = claro).  
Aplicar como clase `dark` / `light` en `<html>` y usar CSS custom properties.  
Añadir un botón en la topbar (escritorio) o en el menú de perfil (móvil).

---

## Pantallas

---

### 1. Acceso / Registro — `accounts/`

**URL:** `/acceso/` (login) · `/registro/` (register)  
**Sin shell:** estas vistas NO usan `base.html`. Tienen su propia página centrada.

**Layout:**
```
Fondo: var(--bg), centrado vertical y horizontal
Tarjeta: max-width 380px, border-radius 18px, border 1px --border, bg --surface, padding 22px
```

**Cabecera:**
```
Logo "6el1" centrado — Bricolage Grotesque 800 30px
Subtítulo: "la grupeta de carretera · acceso privado" — Hanken 500 14px --dim
Margen bajo: 22px
```

**Tab switcher (Entrar / Crear cuenta):**
```
Contenedor: bg --bg, border 1px --border, border-radius 11px, padding 4px, gap 4px
Tabs: flex 1, texto centrado, Hanken 700 13px, padding 9px 0, border-radius 8px
  Activo:   bg --accent, color --ac-text
  Inactivo: bg transparent, color --dim
```

**Campos de formulario:**
```
Label: Hanken 600 12px, color --dim, margin-bottom 6px
Input: height 44px, border-radius 11px, border 1px --border, bg --bg, padding 0 13px, Hanken 500 14px
  Focus: border-color --accent, outline none
```

**Botón primario:**
```
width 100%, padding 13px 0, border-radius 12px
bg --accent, color --ac-text, Hanken 700 15px
Hover: brightness(1.08)
```

**Estado pendiente (solo en registro):**  
Tras enviar el formulario, mostrar aviso:
```
Fondo: var(--accent-soft)
Border: 1px solid var(--border)
Border-radius: 12px
Padding: 12px 13px
Dot ámbar (7px) a la izquierda
Texto: "Tu cuenta queda **pendiente de aprobación**. Un admin o moderador la revisará y recibirás un email cuando esté activa."
Hanken 500 12px, color --dim; la palabra en negrita en color --text
```

**Modelo Django:**
```python
# accounts/models.py
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ROLES = [('miembro','Miembro'),('moderador','Moderador'),('admin','Admin')]
    role = models.CharField(max_length=20, choices=ROLES, default='miembro')
    approved = models.BooleanField(default=False)
    bike = models.CharField(max_length=120, blank=True)
```

---

### 2. Dashboard — `dashboard/index.html`

**URL:** `/`  
**Descripción:** Página principal post-login. Saludo personalizado + evento próximo destacado + stats del club + galería reciente + pódium del mes + blog.

**Bloque hero (2 columnas en escritorio, 1 en móvil):**
```
Grid: repeat(auto-fit, minmax(300px, 1fr)), gap 20px

Col izquierda:
  Saludo: "Buenas, {nombre} 👋" — Bricolage Grotesque 800 38px, letter-spacing -1px
  Subtítulo: texto del próximo evento — Hanken 500 16px --dim, max-width 420px, line-height 1.5
  Botones: "Sí, voy" (primario ámbar) + "Ver la ruta" (secundario bg:--bg border:--border)
  Texto auxiliar: "ya van {N}" — Hanken 600 13px --dim

Col derecha (tarjeta evento destacado, clickable → detalle evento):
  Imagen/placeholder: aspect-ratio 16/8, bg --bg
  Badge fecha: posición absolute top-left, bg --accent, color --ac-text, border-radius 11px
    Día semana: IBM Plex Mono 700 9px uppercase
    Número día: Bricolage Grotesque 800 19px
    Mes: IBM Plex Mono 700 9px uppercase
  Cuerpo tarjeta: padding 16px 18px
    Nombre ruta: Bricolage Grotesque 800 19px
    Detalle: Hanken 500 13px --dim (hora · km · m+ · salida)
    Avatares confirmados: stack de círculos 30px con margin-left -8px
```

**Stats del club (4 tarjetas):**
```
Grid: repeat(auto-fit, minmax(150px, 1fr)), gap 13px
Tarjeta: border-radius 16px, border --border, bg --surface, padding 16px 18px
  Label: Hanken 500 12px --dim
  Valor: Bricolage Grotesque 800 28px + unidad Hanken 600 12px --dim
```
Datos: km del club (mes), Desnivel acumulado, Rutas completadas, Miembros activos.

**Galería reciente + Pódium (2 columnas flex):**
```
flex-wrap wrap, gap 20px

Galería (flex 1 1 360px):
  Título "Lo último de la peña" + enlace "Galería →"
  Grid: repeat(auto-fit, minmax(120px, 1fr)), grid-auto-rows 100px, gap 10px
  Celdas: border-radius 14px, border --border, clickable → álbum

Pódium (flex 1 1 280px):
  Título "Pódium del mes" + enlace "Ranking →"
  3 filas con: badge posición (círculo 30px) + nombre + km
    Pos 1: badge bg --accent color --ac-text
    Pos 2-3: badge bg --surface2 color --text
  Blog debajo: lista de posts recientes (avatar + título + autor + likes)
```

---

### 3. Rutas — listado · `rutas/list.html`

**URL:** `/rutas/`

**Cabecera:**
```
Flex space-between, wrap
Izquierda: título "Rutas" (Bricolage 800 30px) + subtítulo (Hanken 500 14px --dim)
Derecha: botón "+ Subir GPX" (ámbar primario)
```

**Filtros (chips pill):**
```
Flex wrap, gap 8px
Activo: bg --accent, color --ac-text
Inactivo: bg --surface, border --border, color --dim
Opciones: Todas / Carretera / Gravel / Más duras
Border-radius: 20px, padding 7px 14px, Hanken 600 12px
```

**Grid de tarjetas:**
```
repeat(auto-fit, minmax(260px, 1fr)), gap 16px

Tarjeta ruta:
  border-radius 16px, overflow hidden, border --border, bg --surface
  Imagen/mapa: aspect-ratio 16/9, bg --bg (placeholder mapa GPX Leaflet)
    Badge tag (Dura/Media/Suave): top-left, bg --surface border --border, Hanken 600 11px, pill
  Cuerpo: padding 14px 16px
    Nombre: Bricolage 800 17px
    Stats: km (Hanken 600 13px) · m+ · superficie (--dim)
    Pie: border-top --border, padding-top 11px
      Avatar autor (24px círculo) + nombre + fecha (Hanken 500 12px --dim)
```

**Contexto Django:**
```python
# rutas/views.py
def lista_rutas(request):
    rutas = Ruta.objects.filter(activa=True).order_by('-fecha')
    return render(request, 'rutas/list.html', {'rutas': rutas})
```

---

### 4. Rutas — detalle · `rutas/detail.html`

**URL:** `/rutas/<slug>/`

**Breadcrumb:** "← Rutas" (Hanken 600 13px --dim, clickable)

**Cabecera:**
```
Nombre ruta: Bricolage 800 32px, letter-spacing -0.7px
Avatar autor + texto: "{autor} · actualizada el {fecha} · {tipo}" (Hanken 500 13px --dim)
```

**Mapa (Leaflet.js):**
```
border-radius 18px, overflow hidden, border --border, bg --surface
aspect-ratio 21/9
Inicializar Leaflet en <div id="map">, cargar trazado GPX con leaflet-gpx
Badge "Descargar GPX": bottom-right, bg --accent, color --ac-text, border-radius 10px
```

**Stats (4 tarjetas):**
```
repeat(auto-fit, minmax(120px, 1fr)), gap 12px
Distancia / Desnivel+ / Desnivel- / Cota máx.
Estilo idéntico a las del dashboard
```

**Perfil de elevación:**
```
Tarjeta: border-radius 16px, border --border, bg --surface, padding 16px 18px
Título "Perfil de elevación" + nota "extraído del GPX" (Mono 500 11px --dim)
Gráfico: altura 120px, barras flex (gap 3px), cada barra:
  flex:1, border-radius 3px 3px 0 0
  background: linear-gradient(180deg, var(--accent), var(--accent-soft))
  altura proporcional al desnivel relativo (%)
Eje X: 3 etiquetas (0 km / mitad / total) — IBM Plex Mono 500 11px --dim
Implementar con Chart.js (type:'bar', color ámbar) o SVG path
```

---

### 5. Eventos — listado · `eventos/list.html`

**URL:** `/eventos/`

**Listado vertical** de eventos (flex-direction column, gap 13px):
```
Tarjeta evento: flex, align-items center, gap 16px, flex-wrap wrap
  Badge fecha (64px):
    bg --bg, border --border, border-radius 13px, padding 10px 0
    Día semana: IBM Plex Mono 700 10px, color --accent
    Número: Bricolage 800 24px
    Mes: IBM Plex Mono 700 10px --dim
  Info:
    Nombre: Bricolage 800 17px
    Detalle: hora · km · m+ · tipo (Hanken 500 13px --dim)
  Derecha:
    Stack avatares confirmados (28px, margin-left -8px) + "{N} van"
    Botón "Voy": bg --accent, color --ac-text, Hanken 700 12px, padding 7px 18px, border-radius 9px
```

---

### 6. Eventos — detalle + RSVP · `eventos/detail.html`

**URL:** `/eventos/<slug>/`

**Hero con imagen:**
```
border-radius 18px, overflow hidden
Imagen: aspect-ratio 21/8, bg --bg
  Badge fecha: top-left, posición absolute, bg --accent
Cuerpo: padding 20px 22px
  Nombre: Bricolage 800 28px
  Fecha/hora/salida: Hanken 500 14px --dim
```

**Contenido (2 columnas flex):**
```
flex gap 18px, flex-wrap wrap

Col izquierda (flex 1 1 340px):
  - Descripción: Hanken 400 14px/1.6 --text
  - Tarjeta "Ruta asociada": flex, thumbnail (70x54px mapa), datos, "Ver →" ámbar
  - Galería post-evento: grid auto-fit minmax(90px,1fr), rows 78px
    Botón "+ Subir fotos" (Hanken 600 12px --accent)

Col derecha (flex 1 1 240px):
  Tarjeta RSVP:
    Botones "Voy" / "No puedo": flex gap 9px, flex 1, padding 11px 0, border-radius 11px
    "Voy" → bg --accent, color --ac-text
    "No puedo" → bg --bg, border --border, color --text
    Lista confirmados: avatar 28px + nombre + dot verde
    
    HTMX: <button hx-post="/eventos/{id}/rsvp/" hx-target="#lista-confirmados" hx-swap="outerHTML">
```

---

### 7. Galería — álbumes · `galeria/index.html`

**URL:** `/galeria/`

**Grid álbumes:**
```
repeat(auto-fit, minmax(240px, 1fr)), gap 16px

Tarjeta álbum:
  border-radius 16px, overflow hidden, border --border, bg --surface
  Imagen: aspect-ratio 4/3
    Badge contador (bottom-right): "{N} fotos", bg --surface border --border, Hanken 600 11px, pill
  Cuerpo: padding 13px 15px
    Nombre álbum: Bricolage 800 16px
    Fecha: Hanken 500 12px --dim
```

---

### 8. Galería — álbum · `galeria/album.html`

**URL:** `/galeria/<slug>/`

**Cabecera:**
```
Nombre álbum: Bricolage 800 30px
Subtítulo: "{fecha} · {N} fotos · {M} vídeos · subido por {autor}" — Hanken 500 14px --dim
Botón "+ Añadir las mías" (ámbar)
```

**Grid de fotos:**
```
repeat(auto-fit, minmax(150px, 1fr)), grid-auto-rows 140px, gap 10px
Celda: border-radius 13px, border --border, overflow hidden
Click → lightbox (usar GLightbox o similar)
```

---

### 9. Blog — listado · `blog/list.html`

**URL:** `/blog/`

**Post destacado (primero):**
```
border-radius 18px, overflow hidden, border --border, bg --surface, mb 16px
Imagen: aspect-ratio 21/8
Cuerpo: padding 18px 20px
  Categoría: Hanken 600 11px, color --accent, uppercase, letter-spacing .06em
  Título: Bricolage 800 24px, letter-spacing -.4px
  Extracto: Hanken 500 14px --dim, line-height 1.5
  Pie: avatar 26px + autor + fecha + "♥ likes"
```

**Lista de posts restantes:**
```
flex-direction column, gap 12px
Item: flex, align center, gap 14px
  Thumbnail: 64×64px, border-radius 11px, border --border
  Info: título (Bricolage 800 16px) + autor · fecha · likes (Hanken 500 12px --dim)
```

---

### 10. Blog — post detalle · `blog/post.html`

**URL:** `/blog/<slug>/`

**Cabecera del post:**
```
Max-width 680px, margin 0 auto
Categoría: Hanken 600 11px --accent uppercase
Título: Bricolage 800 36px, letter-spacing -.8px, line-height 1.08
Autor: avatar 34px + nombre (Hanken 700 14px) + fecha + "N min de lectura" (Hanken 500 12px --dim)
Imagen principal: aspect-ratio 16/8, border-radius 16px, border --border
```

**Cuerpo del post:**
```
font: Hanken 400 16px, line-height 1.7, color --text
Párrafos: margin-bottom 16px
Citas/blockquote: color --dim, border-left 3px --accent, padding-left 16px
```

**Acciones:**
```
Flex align-items center, gap 10px, border-top/bottom --border, padding 14px 0
Botón "♥ Me gusta": bg --accent, color --ac-text, border-radius 22px, padding 9px 18px, Hanken 700 14px
  HTMX: hx-post="/blog/{id}/like/" hx-target="#like-btn" hx-swap="outerHTML"
Contador comentarios: Hanken 600 13px --dim
```

**Comentarios:**
```
Título "Comentarios": Bricolage 800 18px
Input nuevo comentario: avatar 34px + input (height 44px, border-radius 12px, border --border, bg --bg)
Lista:
  Avatar 34px + nombre (Hanken 700 13px) + fecha (Hanken 500 11px --dim)
  Texto: Hanken 400 14px/1.55 --text
  Gap entre comentarios: 16px
```

---

### 11. Chat · `chat/sala.html`

**URL:** `/chat/`

**Contenedor principal:**
```
border-radius 18px, border --border, bg --surface, height 560px (escritorio)
display flex, flex-direction column, overflow hidden
```

**Cabecera:**
```
height: 66px, border-bottom --border, padding 14px 18px
Icono sala: 38×38px, border-radius 12px, bg --accent, color --ac-text, Bricolage 800 16px
Nombre: Bricolage 800 16px
Subtítulo: "{N} miembros · {M} escribiendo" — Hanken 500 12px --dim
Dot verde (#34c759) a la derecha
```

**Área de mensajes:**
```
flex 1, overflow-y auto, padding 18px, gap 14px
Separador de fecha: texto centrado "— hoy —", Hanken 500 11px --dim

Mensaje:
  Avatar 30px + burbuja
  Mensaje propio: flex-direction row-reverse; bg --accent-soft
  Mensaje ajeno: flex-direction row; bg --surface2
  Burbuja: Hanken 400 14px/1.5, padding 9px 13px, border-radius 14px, border --border
  Cabecera: nombre (Hanken 700 12px) + hora (Hanken 500 10px --dim)
```

**Input:**
```
border-top --border, padding 13px 16px, flex 0 0 auto
Input: flex 1, height 42px, border-radius 13px, border --border, bg --bg, Hanken 500 14px --dim
Botón enviar: 42×42px, border-radius 13px, bg --accent, color --ac-text, "↑" Hanken 700 18px
```

**Implementación:**
```
Opción A (simple): polling AJAX cada 2s con HTMX hx-trigger="every 2s"
Opción B (tiempo real): Django Channels + WebSocket
```

---

### 12. Miembros — directorio · `miembros/list.html`

**URL:** `/miembros/`

**Toggle Ranking / Directorio:**
```
Flex, gap 3px, padding 3px, bg --bg, border --border, border-radius 10px
Activo: bg --accent, color --ac-text, border-radius 7px, padding 6px 13px
Inactivo: color --dim, padding 6px 13px
```

**Grid de miembros:**
```
repeat(auto-fit, minmax(280px, 1fr)), gap 14px

Tarjeta miembro (clickable → perfil):
  flex, align-items center, gap 13px, border-radius 15px, border --border, bg --surface, padding 14px 16px
  Avatar: 46×46px círculo, Bricolage 800 18px
  Info:
    Nombre (Bricolage 800 16px) + badge de rol
      Admin/Moderador: bg --accent, color --ac-text
      Miembro: bg transparent, border --border, color --dim
    Bici: Hanken 500 12px --dim, truncado
  KM (derecha):
    Número: Bricolage 800 18px
    Unidad: "km · jun" Hanken 500 10px --dim
```

---

### 13. Miembros — perfil · `miembros/perfil.html`

**URL:** `/miembros/<username>/`

**Banner + avatar:**
```
Banner: height 120px, bg --bg (imagen si la tiene)
Avatar: 78×78px círculo, margin-top -34px, border 3px solid --surface
Nombre: Bricolage 800 26px, letter-spacing -.4px
Subtítulo: "Miembro desde {año} · {bici}" — Hanken 500 13px --dim
Botón "Editar perfil" (solo si es el propio usuario): bg --bg, border --border
```

**Stats (4 tarjetas):** km totales / rutas hechas / eventos / desnivel mes

**Mis bicis:**
```
Flex column, gap 11px
Tarjeta bici: flex, thumbnail (54×40px placeholder) + nombre + tipo + año
```

**Últimas salidas:**
```
border-radius 14px, border --border, bg --surface, overflow hidden
Fila: nombre ruta (Hanken 600 13px) + fecha (Hanken 500 11px --dim) + km (Bricolage 700 13px)
Border-bottom entre filas
```

---

### 14. Moderación · `miembros/moderacion.html`

**URL:** `/admin-grupeta/registros/`  
**Acceso:** solo `role == 'admin'` o `role == 'moderador'`

**Registros pendientes (columna izquierda):**
```
flex 1 1 320px
Tarjeta por solicitud:
  Avatar (40px) + nombre (Hanken 700 15px) + email + "hace N h" (Hanken 500 12px --dim)
  Botones: "Aprobar" (ámbar) / "Rechazar" (fondo --bg, border --border)
  HTMX:
    hx-post="/admin-grupeta/registros/{id}/aprobar/"
    hx-post="/admin-grupeta/registros/{id}/rechazar/"
    hx-target="closest .tarjeta-registro" hx-swap="outerHTML"
```

**Gestión de roles (columna derecha):**
```
flex 1 1 320px
border-radius 15px, border --border, bg --surface, overflow hidden
Fila por miembro: avatar + nombre + selector de rol (bg --bg, border --border, border-radius 9px)
  <select> con opciones: Miembro / Moderador / Admin
  HTMX: hx-post="/admin-grupeta/rol/{id}/" hx-trigger="change"
```

---

## Interacciones y comportamiento

| Interacción | Implementación recomendada |
|-------------|---------------------------|
| RSVP evento | HTMX `hx-post` + respuesta parcial HTML |
| Like en post | HTMX `hx-post` + swap del botón con nuevo contador |
| Comentario nuevo | HTMX `hx-post` + `hx-target` prepend en lista |
| Chat en tiempo real | Django Channels WebSocket (o polling HTMX cada 2s para MVP) |
| Aprobar/rechazar registro | HTMX `hx-post` + `hx-swap="outerHTML"` elimina la tarjeta |
| Cambio de rol | HTMX `hx-trigger="change"` en `<select>` |
| Subida de GPX | `<form enctype="multipart/form-data">`, backend: `gpxpy` para parsear |
| Mapa de ruta | Leaflet.js + leaflet-gpx; tile OSM o Mapbox |
| Perfil de elevación | Chart.js (bar chart, color --accent) o SVG manual |
| Galería lightbox | GLightbox o PhotoSwipe |
| Tema claro/oscuro | CSS custom properties en `:root`, clase `dark` en `<html>`, localStorage |
| Transiciones de tema | `transition: background .25s ease, color .25s ease` en `body` y tarjetas |

---

## Librerías sugeridas

```
Django 4.x + Python 3.11+
django-allauth          # autenticación
django-channels         # WebSocket chat
htmx 1.9+              # interacciones sin SPA
django-gpx              # modelos GPX
gpxpy                   # parsing de archivos GPX
Leaflet.js 1.9+         # mapas
leaflet-gpx             # render de trazados
Chart.js 4.x            # perfil de elevación
GLightbox               # galería lightbox
Pillow                  # procesado de imágenes
django-imagekit          # thumbnails automáticos
```

---

## Assets necesarios

- Fuentes Google Fonts: Bricolage Grotesque, Hanken Grotesk, IBM Plex Mono (ya referenciados)
- Fotos y GPX: los miembros los subirán en producción; en desarrollo usar datos ficticios
- Mapa tiles: OpenStreetMap (gratuito) o Mapbox (token propio)
- Favicon: texto "6el1" o icono de rueda

---

## Archivos de este paquete

| Archivo | Descripción |
|---------|-------------|
| `README.md` | Este documento — guía de implementación completa |
| `GrupetaWeb 6EL1.dc.html` | Prototipo navegable HTML con las 14 pantallas (referencia visual) |
| `tokens.css` | Variables CSS del sistema de diseño listas para copiar |

---

## Notas finales para Claude Code

1. **Empieza por `base.html`** y los tokens CSS; el resto de plantillas extienden el shell.
2. **`accounts/` primero**: sin login/aprobación el resto no funciona.
3. **HTMX antes que JavaScript propio**: la mayoría de interacciones son `hx-post` + swap parcial.
4. **No copies el HTML del prototipo directamente**: usa Django template tags (`{% for %}`, `{% if %}`, `{% url %}`, `{{ variable }}`), los formularios de Django y los modelos reales.
5. La lógica del tema (claro/oscuro) va en `static/js/theme.js` y se aplica como clase `dark` en `<html>` antes del render para evitar flash.
