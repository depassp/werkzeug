# Changes and notes in Python 3

- HTTP Header
 - datastructures.Header
  - Python 2: Header values treated as (byte) `str`'s
  - Python 3: Header values treated as (unicode) `str`'s
 - http.parse_authorization_header()
  - Python 2: returns (byte) `str`'s for the values
  - Python 3: returns (unicode) `str`'s for the values, assumes `latin1`
 - http.dump_cookie()
  - Python 2: Non-ascii strings for values accepted
  - Python 3: Non-ascii strings for values will raise a `TypeError`. You should urlencode the value. (See [http://stackoverflow.com/questions/1969232/allowed-characters-in-cookies].)
- IRI and URI
 - Python 2: IRI was `unicode`, URI was `str`
 - Python 3: IRI and URI are both (unicode) `str`

## Minor changes

- urls.url_encode()
 - Python 2: default sort behaviour: `int`'s ascending, then `str`'s
 - Python 3: default sort behaviour: lexicographical order
