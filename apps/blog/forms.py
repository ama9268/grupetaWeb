from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'content', 'header_image')
        labels = {
            'title': 'Título',
            'content': 'Contenido',
            'header_image': 'Imagen de cabecera',
        }
        widgets = {
            'content': forms.Textarea(attrs={'class': 'hidden', 'id': 'id_content'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)
        labels = {'content': ''}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe un comentario...'}),
        }
