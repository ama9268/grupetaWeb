from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy, reverse

from apps.accounts.mixins import ApprovedUserMixin
from .models import Post, Comment, Like
from .forms import PostForm, CommentForm


class PostListView(ApprovedUserMixin, ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.select_related('author').all()


class PostDetailView(ApprovedUserMixin, DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['comment_form'] = CommentForm()
        ctx['comments'] = self.object.comments.select_related('author').all()
        ctx['user_liked'] = Like.objects.filter(
            post=self.object, user=self.request.user
        ).exists()
        ctx['likes_count'] = self.object.likes_count()
        return ctx


class PostCreateView(ApprovedUserMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_create.html'

    def form_valid(self, form):
        post = form.save(commit=False)
        post.author = self.request.user
        post.save()
        messages.success(self.request, 'Post publicado correctamente.')
        return redirect('blog:detail', pk=post.pk)


def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
    return redirect('blog:detail', pk=post_id)


def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if comment.author != request.user and request.user.profile.role not in ('admin', 'moderator'):
        raise PermissionDenied
    post_id = comment.post_id
    comment.delete()
    return redirect('blog:detail', pk=post_id)


def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user and request.user.profile.role not in ('admin', 'moderator'):
        raise PermissionDenied
    post.delete()
    messages.success(request, 'Post eliminado.')
    return redirect('blog:list')


def toggle_like(request, post_id):
    if request.method != 'POST':
        return redirect('blog:detail', pk=post_id)
    post = get_object_or_404(Post, pk=post_id)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    likes_count = post.likes_count()
    user_liked = created
    return render(request, 'blog/partials/like_button.html', {
        'post': post,
        'likes_count': likes_count,
        'user_liked': user_liked,
    })
