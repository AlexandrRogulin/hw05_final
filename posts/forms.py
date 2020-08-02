from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            'group': 'Группа',
            'text': 'Сообщение',
            'image': 'Изображение'
        }
        help_texts = {
            'group': 'Выберите группу (необязательно)',
            'text': 'Напишите пост тут :)'
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        text = forms.CharField(widget=forms.Textarea)
        labels = {
            'text': 'Комментарий'
        }
        help_texts = {
            'text': 'Напишите комментарий тут :)'
        }


