from .cloudinary_utils import upload_image, upload_video
from .models import MediaItem


def upload_media_item(user, media_type, file, group=None, title='', album=None):
    """Upload a file to Cloudinary and persist a MediaItem record.

    If ``album`` is provided, the item is linked to it (e.g. an event album)
    and inherits its grupeta; si no, ``group`` es obligatorio (subida suelta).
    """
    if media_type == 'image':
        public_id, url = upload_image(file)
    else:
        public_id, url = upload_video(file)

    return MediaItem.objects.create(
        album=album,
        group=group or album.group,
        uploaded_by=user,
        media_type=media_type,
        cloudinary_public_id=public_id,
        cloudinary_url=url,
        title=title,
    )
