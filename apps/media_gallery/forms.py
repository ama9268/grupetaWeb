import filetype
from django import forms
from .cloudinary_utils import ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES

MAGIC_BYTES_LENGTH = 261  # filetype only needs the first ~261 bytes


class MediaUploadForm(forms.Form):
    media_type = forms.ChoiceField(
        choices=[('image', 'Imagen'), ('video', 'Vídeo')],
        label='Tipo de archivo',
    )
    file = forms.FileField(label='Archivo')
    title = forms.CharField(max_length=200, required=False, label='Título (opcional)')
    album = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def clean(self):
        cleaned = super().clean()
        media_type = cleaned.get('media_type')
        file = cleaned.get('file')

        if not (file and media_type):
            return cleaned

        header = file.read(MAGIC_BYTES_LENGTH)
        file.seek(0)

        kind = filetype.guess(header)
        if kind is None:
            raise forms.ValidationError('No se pudo determinar el tipo del archivo. Comprueba que el archivo no esté corrupto.')

        if media_type == 'image' and kind.mime not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError(
                f'Formato de imagen no válido ({kind.mime}). Usa JPG, PNG, WebP o GIF.'
            )
        if media_type == 'video' and kind.mime not in ALLOWED_VIDEO_TYPES:
            raise forms.ValidationError(
                f'Formato de vídeo no válido ({kind.mime}). Usa MP4, MOV o AVI.'
            )

        return cleaned
