from django import forms
from .models import Route

MAX_GPX_SIZE = 10 * 1024 * 1024  # 10 MB
GPX_HEADER_BYTES = 512


def _is_valid_gpx(file) -> bool:
    """Check the first bytes of a file to confirm it is XML containing a <gpx element."""
    header = file.read(GPX_HEADER_BYTES)
    file.seek(0)
    # Strip UTF-8 BOM if present
    if header.startswith(b'\xef\xbb\xbf'):
        header = header[3:]
    try:
        text = header.decode('utf-8', errors='ignore').strip().lower()
    except Exception:
        return False
    return ('<gpx' in text) or (text.startswith('<?xml') and 'gpx' in text)


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ('title', 'description', 'gpx_file')
        labels = {
            'title': 'Título de la ruta',
            'description': 'Descripción',
            'gpx_file': 'Archivo GPX',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_gpx_file(self):
        file = self.cleaned_data['gpx_file']
        if file.size > MAX_GPX_SIZE:
            raise forms.ValidationError('El archivo GPX no puede superar 10 MB.')
        if not _is_valid_gpx(file):
            raise forms.ValidationError(
                'El archivo no parece un GPX válido. Comprueba que contenga datos de ruta en formato XML/GPX.'
            )
        return file
