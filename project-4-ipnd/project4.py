# -*- coding: utf-8 -*-
import urllib
import os
import sys
import atexit

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.datastore.datastore_query import Cursor

import webapp2
import jinja2
import cgi

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

class Handler(webapp2.RequestHandler):
  """Handler class to handle jinja templates.

  We use jinja2 to use a template html and replace the values we want
  inside this template
  """

  def render(self, template, **kw):
    """Main method to call from our get methods later on"""
    self.write(self.render_str(template,**kw))

  def render_str(self, template, **params):
    """This calls our jinja template we specify and returns a
    processed string.
    """
    template = jinja_env.get_template(template)
    return template.render(params)

  def write(self, *a, **kw):
    """This will write our response HTML back to the client"""
    self.response.write(*a, **kw)

TEST_NO_CONTENT = "Please check for posts below"
POST_CONTENT_TITLE = 'User Added Content'

def post_key(post_space=POST_CONTENT_TITLE):

    return ndb.Key('Post', post_space)

class Author(ndb.Model):
    """Sub model for representing an author."""
    identity = ndb.StringProperty(indexed=True)
    name = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Post(ndb.Model):
    """A main model for representing an individual post entry."""
    author = ndb.StructuredProperty(Author)
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class MainPage(Handler):
    def get(self):
        post_space = self.request.get('post_space',POST_CONTENT_TITLE)
        error_message = self.request.get('error_message',TEST_NO_CONTENT)
        if post_space == POST_CONTENT_TITLE.lower(): post_space = POST_CONTENT_TITLE

        posts_to_fetch = 10

        cursor_url = self.request.get('continue_posts')

        arguments = {'post_space': post_space}
        error_message = {error_message}
        posts_query = Post.query(ancestor = post_key(post_space)).order(-Post.date)

        posts, cursor, more = posts_query.fetch_page(posts_to_fetch, start_cursor =
            Cursor(urlsafe=cursor_url))

        if more:
            arguments['continue_posts'] = cursor.urlsafe()

        arguments['posts'] = posts

        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            user = 'Anonymous Poster'
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        arguments['user_name'] = user
        arguments['url'] = url
        arguments['url_linktext'] = url_linktext
        arguments['error_message'] = error_message
        self.render('posts.html', **arguments)

class PostWall(webapp2.RequestHandler):
    def post(self):

        post_space = self.request.get('post_space',POST_CONTENT_TITLE)
        post = Post(parent=post_key(post_space))

        if users.get_current_user():
            post.author = Author(
                    identity=users.get_current_user().user_id(),
                    name=users.get_current_user().nickname(),
                    email=users.get_current_user().email())

        content = self.request.get('content')

        if not content:
            TEST_NO_CONTENT = "The post you just entered contained no content"
            self.redirect('/')
        elif type(content) != unicode:
            post.content = unicode(self.request.get('content'), 'utf-8')
        else:
            post.content = self.request.get('content')

            post.put()

        query_params = {'post_space': post_space}
        self.redirect('/?' + urllib.urlencode(query_params))

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', PostWall),
], debug=True)