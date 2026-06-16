from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy

from apps.accounts.mixins import ApprovedUserMixin
from .models import MediaItem
from .forms import MediaUploadForm
from .services import upload_media_item


class GalleryListView(ApprovedUserMixin, ListView):
    model = MediaItem
    template_name = 'media_gallery/gallery_list.html'
    context_object_name = 'items'
    paginate_by = 24

    def get_queryset(self):
        return MediaItem.objects.select_related('uploaded_by').all()


class MediaUploadView(ApprovedUserMixin, CreateView):
    template_name = 'media_gallery/media_upload.html'
    form_class = MediaUploadForm
    success_url = reverse_lazy('media_gallery:list')

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        try:
            upload_media_item(
                user=request.user,
                media_type=form.cleaned_data['media_type'],
                file=form.cleaned_data['file'],
                title=form.cleaned_data.get('title', ''),
            )
        except Exception as e:
            messages.error(request, f'Error al subir el archivo: {e}')
            return render(request, self.template_name, {'form': form})

        messages.success(request, 'Archivo subido correctamente.')
        return redirect(self.success_url)


def delete_media(request, item_id):
    if request.method != 'POST':
        return redirect('media_gallery:list')
    item = get_object_or_404(MediaItem, pk=item_id)
    if item.uploaded_by != request.user and request.user.profile.role not in ('admin', 'moderator'):
        raise PermissionDenied
    item.delete()
    messages.success(request, 'Archivo eliminado.')
    return redirect('media_gallery:list')
