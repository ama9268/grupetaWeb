import filetype
from django import forms
from django.conf import settings

from apps.media_gallery.cloudinary_utils import ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES

MAGIC_BYTES_LENGTH = 261  # filetype solo necesita los primeros ~261 bytes

DEFAULT_MAX_IMAGE_UPLOAD_SIZE = 10 * 1024 * 1024   # 10 MB
DEFAULT_MAX_VIDEO_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB


def _max_upload_size(media_type):
    if media_type == 'image':
        return getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE', DEFAULT_MAX_IMAGE_UPLOAD_SIZE)
    return getattr(settings, 'MAX_VIDEO_UPLOAD_SIZE', DEFAULT_MAX_VIDEO_UPLOAD_SIZE)


class ChatAttachmentForm(forms.Form):
    """Valida un adjunto (imagen o vídeo) antes de subirlo a Cloudinary.

    El `media_type` NO se toma del cliente: se deduce de los magic bytes del
    propio archivo, para no fiarse de un campo manipulable.
    """
    file = forms.FileField(label='Archivo')
    # Pie de foto opcional que acompaña al adjunto.
    caption = forms.CharField(max_length=2000, required=False)

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get('file')
        if not file:
            return cleaned

        header = file.read(MAGIC_BYTES_LENGTH)
        file.seek(0)

        kind = filetype.guess(header)
        if kind is None:
            raise forms.ValidationError(
                'No se pudo determinar el tipo del archivo. Comprueba que no esté corrupto.'
            )

        if kind.mime in ALLOWED_IMAGE_TYPES:
            media_type = 'image'
        elif kind.mime in ALLOWED_VIDEO_TYPES:
            media_type = 'video'
        else:
            raise forms.ValidationError(
                f'Formato no válido ({kind.mime}). Imágenes: JPG, PNG, WebP, GIF. '
                f'Vídeos: MP4, MOV, AVI.'
            )

        limit = _max_upload_size(media_type)
        if file.size > limit:
            mb = limit // (1024 * 1024)
            raise forms.ValidationError(
                f'El archivo supera el tamaño máximo permitido ({mb} MB).'
            )

        cleaned['media_type'] = media_type
        return cleaned
