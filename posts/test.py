import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from posts.models import Comment, Follow, Group, Post

TEST_CACHES = {
    'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
User = get_user_model()


class TestProfileAndPosts(TestCase):

    def setUp(self):
        self.logged_client = Client()
        self.client = Client()

        self.user = User.objects.create_user(
            username='UserForTest', 
            email='Test@test.ru',
            password='AsefdasDSa32'
        )
        self.text = 'Тестовое сообщение'
        self.logged_client.force_login(self.user)
        self.group = Group.objects.create(title='Test', slug='test_group')
        self.following = User.objects.create_user(
            username='TestFollowing', password='password')

    def test_profile_created(self):
        profile_url = reverse('profile', kwargs={'username': self.user})
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, template_name='profile.html')

    def test_unauthorized_redirect(self):
        self.client.post(reverse('new-post'), follow=True)
        login_url = self.client.post(reverse('login'))
        self.assertTemplateUsed(
            login_url,
            template_name='registration/login.html'
        )

    def test_post(self):
        post_test = self.logged_client.post(
            reverse('new-post'),
            {'text': self.text}, 
            follow=True
        )
        self.assertEqual(post_test.status_code, 200)
        self.assertEqual(1, Post.objects.filter(text=self.text).exists())
        created_post = Post.objects.get(text=self.text)
        self.assertIn(self.text, created_post.text)

    def check_contain_post(self, url, text, group=None, user=None):
        self.assertContains(url, text=text, count=1, status_code=200)

    @override_settings(CACHES=TEST_CACHES)
    def test_post_view(self):
        self.logged_client.post(
            reverse(
                'new-post'), 
                {'text': self.text, 'group': self.group.id},
                follow=True
            )
        post = Post.objects.get(text=self.text)
        url_list = [
            self.logged_client.get(reverse('index')),
            self.logged_client.get(
                reverse(
                    'profile', 
                    kwargs={'username': self.user}
                )
            ),
            self.logged_client.get(
                reverse(
                    'group', 
                    kwargs={'slug': self.group.slug}
                )
            ),
            self.logged_client.get(
                reverse(
                    'post', 
                    kwargs={
                        'username': self.user,
                        'post_id': post.id}
                )
            )
        ]
        for url in url_list:
            with self.subTest(url=url):
                self.check_contain_post(
                    url, 
                    text=self.text, 
                    group=self.group,
                    user=self.user
                )

    @override_settings(CACHES=TEST_CACHES)
    def test_post_edit(self):
        post = Post.objects.create(text=self.text, author=self.user)
        new_text = 'Измененное сообщение'
        self.logged_client.post(
            reverse('post_edit', kwargs={
                'username': self.user,
                'post_id': post.id
            }),
            {'text': new_text, 'group': self.group.id}
        )
        url_list = [
            self.logged_client.get(reverse('index')),
            self.logged_client.get(
                reverse('profile', kwargs={'username': self.user})),
            self.logged_client.get(
                reverse('group', kwargs={'slug': self.group.slug})),
            self.logged_client.get(reverse('post', kwargs={
                'username': self.user,
                'post_id': post.id}))
        ]
        for url in url_list:
            with self.subTest(url=url):
                self.check_contain_post(url, text=new_text, group=self.group,
                                        user=self.user)

    def test_404(self):
        response = self.client.get('request/wrong/url/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'misc/404.html')


class TestImg(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='TestCat',
            password='ewiwjmpQWed123f'
        )
        self.client.force_login(self.user)
        self.group = Group.objects.create(
            title='Cats',
            slug='cats',
            description='CatsCats',
        )
        self.post = Post.objects.create(
            text='hi', 
            group=self.group,
            author=self.user
        )
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as img:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(img, 'PNG')
        self.image = open(img.name, mode='rb')

        with tempfile.NamedTemporaryFile(
            suffix='.doc',
            delete=False
        ) as not_img:
            not_img.write(b'test')
        self.not_image = open(not_img.name, 'rb')

    @override_settings(CACHES=TEST_CACHES)
    def test_pages_have_img(self):
        with self.image as img:
            self.client.post(
                reverse(
                    'post_edit',
                    kwargs={'username': self.user, 'post_id': self.post.id}
                ),
                    {'group': self.group.id,
                    'text': 'post with image',
                    'image': img}, redirect=True)

        tag = '<img class='

        response_profile = self.client.get(reverse(
            'profile', kwargs={'username': self.user.username}))
        response_index = self.client.get(reverse('index'))
        response_group = self.client.get(reverse(
            'group', kwargs={'slug': self.group.slug}))

        self.assertContains(response_index, tag)
        self.assertContains(response_profile, tag)
        self.assertContains(response_group, tag)

    def test_wrong_format(self):
        with self.not_image as img:
            wrong_img = self.client.post(
                reverse(
                    'post_edit',
                    kwargs={
                        'username': self.user,
                        'post_id': self.post.id
                        }
                ),
                {'group': self.group.id,
                'text': 'post with image',
                'image': img
                },
                 redirect=True)

        error = ('Загрузите правильное изображение. Файл, который вы '
                 'загрузили, поврежден или не является изображением.')
        self.assertFormError(wrong_img, 'form', 'image', error)

    def tearDown(self):
        self.image.close()
        self.not_image.close()


class TestCache(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='TestUser',
            password='ASKnfbg123_2'
        )
        self.client.force_login(self.user)

    def test_cache(self):
        response = self.client.post(
            reverse('new-post'),
            data={'text': 'Test text'},
            follow=True
        )
        post = Post.objects.first()
        self.assertContains(response, 'Test text')
        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Test text')


class TestFollowSystem(TestCase):
    def setUp(self):
        self.client = Client()
        self.following = User.objects.create_user(
            username='TestFollowing', 
            password='password'
        )
        self.follower = User.objects.create_user(
            username='TestFollower',
            password='password'
        )
        self.user = User.objects.create_user(
            username='user',
            password='password'
        )
        self.post = Post.objects.create(
            author=self.following,
            text='FollowTest'
        )
        self.client.force_login(self.follower)
        self.link = Follow.objects.filter(
            user=self.follower,
            author=self.following
        )

    def test_follow(self):
        response = self.client.get(
            reverse(
                'profile_follow', 
                kwargs={'username': self.following}
            ), 
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.link.exists())
        self.assertEqual(1, Follow.objects.count())

    def test_unfollow(self):
        response = self.client.get(
            reverse(
                'profile_unfollow', 
                kwargs={'username': self.following}
                ),
            follow=True
            )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.link.exists())
        self.assertEqual(0, Follow.objects.count())

    def test_follow_index(self):
        Follow.objects.create(user=self.follower, author=self.following)
        follow_index_url = reverse('follow_index')
        response = self.client.get(follow_index_url)
        self.assertContains(response, self.post.text)
    
    def test_not_follower_index(self):
        response = self.client.get(reverse('follow_index'))
        self.assertNotContains(response, self.post.text)


class TestComments(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password=12345
        )
        self.text = 'test_text'
        self.post = Post.objects.create(
            text=self.text, 
            author=self.user
        )
        self.commenting_user = User.objects.create_user(
            username='commenting_user',
            password=12345
        )
        self.comment_text = 'test_comment'


    def test_auth_user_commenting(self):
        self.client.force_login(self.commenting_user)
        response = self.client.post(
            reverse(
                'add_comment', 
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.pk
                }
            ),
            {'text': self.comment_text}, 
            follow=True
        )
        self.assertContains(response, self.comment_text)

    def test_anon_user_commenting(self):
        response = self.client.post(
            reverse(
                'add_comment', 
                kwargs={
                    'username': self.user.username,
                    'post_id': self.post.pk
                }
            ),
            {'text': self.comment_text}, 
            follow=True
        )
        self.assertNotContains(response, self.comment_text)
