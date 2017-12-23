libtivomind
===========

A library that handles the RPC connection to a TiVo using the Mind RPC
protocal.  Based to a large extent on reviewing the Mind protocol
commands in `kmttg <https://sourceforge.net/projects/kmttg/>`__.

``libtivomind`` has no external dependencies beyond the Python
standard library. However, to create connections you will need a
certificate (and associated password) from TiVo.

The following is a simple example showing how to query for upcoming
showings ("offers") by title, and how to get series ("collection")
info for that offer:

.. code:: python

    >>> from libtivomind import api
    >>> from textwrap import wrap

    >>> mind = api.Mind.new_local_session(cert_path='/path/to/cert.pem',
                                          cert_password='YourCertPassword',
                                          address='ip.address.of.tivo',
                                          mak='YourTiVosMAK',
                                          port=1413)
    >>> filt = api.SearchFilter()
    >>> filt.by_title('Start Trek')
    >>> offers = mind.offer_search(filt=filt, limit=5)
    >>> offers[0]['title']
    'Star Trek'
    >>> print('\n'.join(wrap(offers[0]['description'], 60)))
    A cloud-like creature detours the shuttlecraft Galileo to a
    remote planetoid, where the crew, including Kirk, Spock and
    an ailing Federation commissioner (Elinor Donahue), are to
    provide its sole inhabitant with companionship---forever.
    Cochrane: Glenn Co
    >>> filt = api.SearchFilter()
    >>> filt.by_collection_id(offers[0])
    >>> cols = mind.collection_search(filt=filt)
    >>> print('\n'.join(wrap(cols[0]['description'])))
    Capt. Kirk, Mr. Spock, Dr. McCoy and the USS Enterprise crew seek out
    new civilizations in this seminal sci-fi series. The ship's five-year
    mission may have only lasted three seasons on NBC, but its impact has
    proved timeless. By the 1970s, its rabid fans---dubbed Trekkers---
    turned the show into a pop-culture phenomenon and syndication
    juggernaut that yielded a merchandising boom, a number of hit sequel
    and prequel spin-off TV series, a successful movie franchise and even
    a children's cartoon.


Continuing from the above, the following shows how to send a remote control
key-press to the TiVo:

.. code:: python

    >>> mind.send_key(api.RemoteKey.liveTv)

