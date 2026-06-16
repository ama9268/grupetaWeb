import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

# PNG magic bytes (first 8 bytes of any valid PNG)
PNG_MAGIC = b'\x89PNG\r\n\x1a\n' + b'\x00' * 253


@pytest.mark.django_db
def test_invalid_mime_rejected_before_upload(member_client):
    """A file with no recognizable magic bytes must fail form validation
    and must NOT reach the Cloudinary upload service."""
    fake_file = SimpleUploadedFile(
        'foto.jpg', b'esto no es una imagen', content_type='image/jpeg'
    )
    with patch('apps.media_gallery.views.upload_media_item') as mock_upload:
        response = member_client.post(
            reverse('media_gallery:upload'),
            {'media_type': 'image', 'file': fake_file},
        )
        mock_upload.assert_not_called()

    assert response.status_code == 200


@pytest.mark.django_db
def test_valid_png_passes_mime_check(member_client):
    """A file with valid PNG magic bytes passes MIME validation
    (service call is mocked to avoid real Cloudinary upload)."""
    png_file = SimpleUploadedFile('foto.png', PNG_MAGIC, content_type='image/png')
    with patch('apps.media_gallery.views.upload_media_item') as mock_upload:
        mock_upload.return_value = None
        member_client.post(
            reverse('media_gallery:upload'),
            {'media_type': 'image', 'file': png_file},
        )
        mock_upload.assert_called_once()
