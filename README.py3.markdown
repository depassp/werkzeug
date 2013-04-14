# Werkzeug in Python 3

## Changes and notes

- About `PATH_INFO`
 - Python 2: `environ['PATH_INFO']` was a (byte) `str`.  You could pass `environ['PATH_INFO']` directly to `MapAdapter`s
 - Python 3: `environ['PATH_INFO']` is now a (unicode) `str`; and if you want to use it, you have to encode it in ISO 5589-1 (`latin1`).
  - `MapAdapter.match()` and `MapAdapter.dispatch()` now has separate arguments for path: `path` and `path_info`.  Use `path` for the correctly decoded unicode strings; use `path_info` for directly passing `environ['PATH_INFO']`.
- HTTP header
 - `datastructures.Header`
  - Python 2: Header values treated as (byte) `str`'s
  - Python 3: Header values treated as (unicode) `str`'s
 - `http.parse_authorization_header()`
  - Python 2: returns (byte) `str`'s for the values
  - Python 3: returns (unicode) `str`'s for the values, assumes `latin1`
 - `http.dump_cookie()`
  - Python 2: Non-ascii strings for values accepted
  - Python 3: Non-ascii strings for values will raise a `TypeError`.  You should urlencode the values. (See http://stackoverflow.com/questions/1969232/allowed-characters-in-cookies for the incompatibility issues.)
- New function
 - `security.safe_bytes_cmp()`

### URL

- IRI and URI
 - Python 2: IRI was a `unicode`, URI was a `str`
 - Python 3: IRI and URI are both (unicode) `str`
- `urls.url_decode_stream()` supports both `BytesIO`/`StringIO`.
- `urls.url_encode()`
 - Python 2: default sort behaviour: `int`'s ascending, then `str`'s
 - Python 3: default sort behaviour: lexicographical order

## Porting your WSGI applications

- Return `bytes`, not `str`. (See also http://www.python.org/dev/peps/pep-3333/#a-note-on-string-types )

```python
def application(environ, start_response):
    # use str here
    start_response('200 OK', [('Content-Type', 'text/plain;charset=utf-8')])
    return [b'Hello, Python 3!']  # use bytes
    return ['Hello, Python 3!']  # error
```

- If you want to use `environ['PATH_INFO']` directly, encode it once in ISO 8859-1 (`latin1`).
