import cloudinary.uploader

ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/quicktime', 'video/x-msvideo']


def upload_image(file_obj):
    result = cloudinary.uploader.upload(
        file_obj,
        folder='grupetaweb/images/',
        transformation=[{'fetch_format': 'webp', 'quality': 'auto'}],
    )
    return result['public_id'], result['secure_url']


def upload_video(file_obj):
    result = cloudinary.uploader.upload(
        file_obj,
        resource_type='video',
        folder='grupetaweb/videos/',
    )
    return result['public_id'], result['secure_url']


def delete_asset(public_id, resource_type='image'):
    """Elimina un asset de Cloudinary (best-effort). No lanza si falla el borrado."""
    if not public_id:
        return
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type, invalidate=True)
    except Exception:
        # El borrado de limpieza no debe romper la petición del usuario.
        pass
