from django import forms

from .models import Group


class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'description', 'logo')
        labels = {
            'name': 'Nombre de la grupeta',
            'description': 'Descripción',
            'logo': 'Logo (opcional)',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'logo':
                field.widget.attrs.setdefault('class', 'input')
