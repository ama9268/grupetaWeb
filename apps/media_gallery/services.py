from .cloudinary_utils import upload_image, upload_video
from .models import MediaItem


def upload_media_item(user, media_type, file, title=''):
    """Upload a file to Cloudinary and persist a MediaItem record."""
    if media_type == 'image':
        public_id, url = upload_image(file)
    else:
        public_id, url = upload_video(file)

    return MediaItem.objects.create(
        uploaded_by=user,
        media_type=media_type,
        cloudinary_public_id=public_id,
        cloudinary_url=url,
        title=title,
    )
