# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.wsgi
    ~~~~~~~~~~~~~~~~~~~~~~~

    Tests the WSGI utilities.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import unittest
import collections
from os import path

from six import BytesIO, PY3

from werkzeug.testsuite import WerkzeugTestCase

from werkzeug.wrappers import BaseResponse
from werkzeug.exceptions import BadRequest, ClientDisconnected
from werkzeug.test import Client, create_environ, run_wsgi_app
from werkzeug import wsgi


class WSGIUtilsTestCase(WerkzeugTestCase):

    def test_shareddatamiddleware_get_file_loader(self):
        app = wsgi.SharedDataMiddleware(None, {})
        assert isinstance(app.get_file_loader('foo'), collections.Callable)

    def test_shared_data_middleware(self):
        def null_application(environ, start_response):
            start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
            yield b'NOT FOUND'
        app = wsgi.SharedDataMiddleware(null_application, {
            '/':        path.join(path.dirname(__file__), 'res'),
            '/sources': path.join(path.dirname(__file__), 'res'),
            '/pkg':     ('werkzeug.debug', 'shared')
        })

        for p in '/test.txt', '/sources/test.txt':
            app_iter, status, headers = run_wsgi_app(app, create_environ(p))
            self.assert_equal(status, '200 OK')
            self.assert_equal(b''.join(app_iter).strip(), b'FOUND')

        app_iter, status, headers = run_wsgi_app(app, create_environ('/pkg/debugger.js'))
        contents = b''.join(app_iter)
        assert b'$(function() {' in contents

        app_iter, status, headers = run_wsgi_app(app, create_environ('/missing'))
        self.assert_equal(status, '404 NOT FOUND')
        self.assert_equal(b''.join(app_iter).strip(), b'NOT FOUND')

    def test_get_host(self):
        env = {'HTTP_X_FORWARDED_HOST': 'example.org',
               'SERVER_NAME': 'bullshit', 'HOST_NAME': 'ignore me dammit'}
        self.assert_equal(wsgi.get_host(env), 'example.org')
        assert wsgi.get_host(create_environ('/', 'http://example.org')) \
            == 'example.org'

    def test_responder(self):
        def foo(environ, start_response):
            return BaseResponse(b'Test')
        client = Client(wsgi.responder(foo), BaseResponse)
        response = client.get('/')
        self.assert_equal(response.status_code, 200)
        self.assert_equal(response.data, b'Test')

    def test_pop_path_info(self):
        original_env = {'SCRIPT_NAME': '/foo', 'PATH_INFO': '/a/b///c'}

        # regular path info popping
        def assert_tuple(script_name, path_info):
            self.assert_equal(env.get('SCRIPT_NAME'), script_name)
            self.assert_equal(env.get('PATH_INFO'), path_info)
        env = original_env.copy()
        pop = lambda: wsgi.pop_path_info(env)

        assert_tuple('/foo', '/a/b///c')
        self.assert_equal(pop(), 'a')
        assert_tuple('/foo/a', '/b///c')
        self.assert_equal(pop(), 'b')
        assert_tuple('/foo/a/b', '///c')
        self.assert_equal(pop(), 'c')
        assert_tuple('/foo/a/b///c', '')
        assert pop() is None

    def test_peek_path_info(self):
        env = {'SCRIPT_NAME': '/foo', 'PATH_INFO': '/aaa/b///c'}

        self.assert_equal(wsgi.peek_path_info(env), 'aaa')
        self.assert_equal(wsgi.peek_path_info(env), 'aaa')

    def test_limited_stream(self):
        class RaisingLimitedStream(wsgi.LimitedStream):
            def on_exhausted(self):
                raise BadRequest('input stream exhausted')

        io = BytesIO(b'123456')
        stream = RaisingLimitedStream(io, 3)
        self.assert_equal(stream.read(), b'123')
        self.assert_raises(BadRequest, stream.read)

        io = BytesIO(b'123456')
        stream = RaisingLimitedStream(io, 3)
        self.assert_equal(stream.tell(), 0)
        self.assert_equal(stream.read(1), b'1')
        self.assert_equal(stream.tell(), 1)
        self.assert_equal(stream.read(1), b'2')
        self.assert_equal(stream.tell(), 2)
        self.assert_equal(stream.read(1), b'3')
        self.assert_equal(stream.tell(), 3)
        self.assert_raises(BadRequest, stream.read)

        io = BytesIO(b'123456\nabcdefg')
        stream = wsgi.LimitedStream(io, 9)
        self.assert_equal(stream.readline(), b'123456\n')
        self.assert_equal(stream.readline(), b'ab')

        io = BytesIO(b'123456\nabcdefg')
        stream = wsgi.LimitedStream(io, 9)
        self.assert_equal(stream.readlines(), [b'123456\n', b'ab'])

        io = BytesIO(b'123456\nabcdefg')
        stream = wsgi.LimitedStream(io, 9)
        self.assert_equal(stream.readlines(2), [b'12'])
        self.assert_equal(stream.readlines(2), [b'34'])
        self.assert_equal(stream.readlines(), [b'56\n', b'ab'])

        io = BytesIO(b'123456\nabcdefg')
        stream = wsgi.LimitedStream(io, 9)
        self.assert_equal(stream.readline(100), b'123456\n')

        io = BytesIO(b'123456\nabcdefg')
        stream = wsgi.LimitedStream(io, 9)
        self.assert_equal(stream.readlines(100), [b'123456\n', b'ab'])

        io = BytesIO(b'123456')
        stream = wsgi.LimitedStream(io, 3)
        self.assert_equal(stream.read(1), b'1')
        self.assert_equal(stream.read(1), b'2')
        self.assert_equal(stream.read(), b'3')
        self.assert_equal(stream.read(), b'')

        io = BytesIO(b'123456')
        stream = wsgi.LimitedStream(io, 3)
        self.assert_equal(stream.read(-1), b'123')

    def test_limited_stream_disconnection(self):
        io = BytesIO(b'A bit of content')

        # disconnect detection on out of bytes
        stream = wsgi.LimitedStream(io, 255)
        with self.assert_raises(ClientDisconnected):
            stream.read()

        # disconnect detection because file close
        io = BytesIO(b'x' * 255)
        io.close()
        stream = wsgi.LimitedStream(io, 255)
        with self.assert_raises(ClientDisconnected):
            stream.read()

    def test_path_info_extraction(self):
        x = wsgi.extract_path_info('http://example.com/app', '/app/hello')
        self.assert_equal(x, u'/hello')
        x = wsgi.extract_path_info('http://example.com/app',
                                   'https://example.com/app/hello')
        self.assert_equal(x, u'/hello')
        x = wsgi.extract_path_info('http://example.com/app/',
                                   'https://example.com/app/hello')
        self.assert_equal(x, u'/hello')
        x = wsgi.extract_path_info('http://example.com/app/',
                                   'https://example.com/app')
        self.assert_equal(x, u'/')
        x = wsgi.extract_path_info(u'http://☃.net/', u'/fööbär')
        self.assert_equal(x, u'/fööbär')
        x = wsgi.extract_path_info(u'http://☃.net/x', u'http://☃.net/x/fööbär')
        self.assert_equal(x, u'/fööbär')

        env = create_environ(u'/fööbär', u'http://☃.net/x/')
        x = wsgi.extract_path_info(env, u'http://☃.net/x/fööbär')
        self.assert_equal(x, u'/fööbär')

        x = wsgi.extract_path_info('http://example.com/app/',
                                   'https://example.com/a/hello')
        assert x is None
        x = wsgi.extract_path_info('http://example.com/app/',
                                   'https://example.com/app/hello',
                                   collapse_http_schemes=False)
        assert x is None

    def test_get_host_fallback(self):
        assert wsgi.get_host({
            'SERVER_NAME':      'foobar.example.com',
            'wsgi.url_scheme':  'http',
            'SERVER_PORT':      '80'
        }) == 'foobar.example.com'
        assert wsgi.get_host({
            'SERVER_NAME':      'foobar.example.com',
            'wsgi.url_scheme':  'http',
            'SERVER_PORT':      '81'
        }) == 'foobar.example.com:81'

    def test_multi_part_line_breaks(self):
        data = b'abcdef\r\nghijkl\r\nmnopqrstuvwxyz\r\nABCDEFGHIJK'
        test_stream = BytesIO(data)
        lines = list(wsgi.make_line_iter(test_stream, limit=len(data), buffer_size=16))
        self.assert_equal(lines, [b'abcdef\r\n', b'ghijkl\r\n', b'mnopqrstuvwxyz\r\n', b'ABCDEFGHIJK'])

        data = b'abc\r\nThis line is broken by the buffer length.\r\nFoo bar baz'
        test_stream = BytesIO(data)
        lines = list(wsgi.make_line_iter(test_stream, limit=len(data), buffer_size=24))
        self.assert_equal(lines, [b'abc\r\n', b'This line is broken by the buffer length.\r\n', b'Foo bar baz'])

    def test_multi_part_line_breaks_problematic(self):
        data = b'abc\rdef\r\nghi'
        for x in range(1, 10):
            test_stream = BytesIO(data)
            lines = list(wsgi.make_line_iter(test_stream, limit=len(data), buffer_size=4))
            assert lines == [b'abc\r', b'def\r\n', b'ghi']

    def test_iter_functions_support_iterators(self):
        data = [b'abcdef\r\nghi', b'jkl\r\nmnopqrstuvwxyz\r', b'\nABCDEFGHIJK']
        lines = list(wsgi.make_line_iter(data))
        self.assert_equal(lines, [b'abcdef\r\n', b'ghijkl\r\n', b'mnopqrstuvwxyz\r\n', b'ABCDEFGHIJK'])

    def test_make_chunk_iter(self):
        data = [b'abcdefXghi', b'jklXmnopqrstuvwxyzX', b'ABCDEFGHIJK']
        rv = list(wsgi.make_chunk_iter(data, 'X'))
        self.assert_equal(rv, [b'abcdef', b'ghijkl', b'mnopqrstuvwxyz', b'ABCDEFGHIJK'])

        data = b'abcdefXghijklXmnopqrstuvwxyzXABCDEFGHIJK'
        test_stream = BytesIO(data)
        rv = list(wsgi.make_chunk_iter(test_stream, 'X', limit=len(data), buffer_size=4))
        self.assert_equal(rv, [b'abcdef', b'ghijkl', b'mnopqrstuvwxyz', b'ABCDEFGHIJK'])

    def test_lines_longer_buffer_size(self):
        data = b'1234567890\n1234567890\n'
        for bufsize in range(1, 15):
            lines = list(wsgi.make_line_iter(BytesIO(data), limit=len(data), buffer_size=4))
            self.assert_equal(lines, [b'1234567890\n', b'1234567890\n'])

    def test_pep3333_path_info(self):
        if PY3:
            env = create_environ(u'/föö-bar', u'http://☃.example.com')
            self.assert_equal(env['PATH_INFO'], u'/föö-bar'.encode('utf-8').decode('latin1'))
            self.assert_equal(wsgi.get_current_url(env), 'http://xn--n3h.example.com/f%C3%B6%C3%B6-bar')

            env = create_environ('/f%C3%B6%C3%B6-bar', u'http://☃.example.com')
            self.assert_equal(env['PATH_INFO'], u'/föö-bar'.encode('utf-8').decode('latin1'))
            self.assert_equal(wsgi.get_current_url(env), 'http://xn--n3h.example.com/f%C3%B6%C3%B6-bar')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(WSGIUtilsTestCase))
    return suite
