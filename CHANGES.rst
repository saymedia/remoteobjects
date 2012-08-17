remoteobjects Changelog
=======================

1.2.2 (2012-08-xx)
------------------

Carl Meyer (3):
      Fixed failing get_bad_encoding test.
      Support forwards-reference in Link
      Don't try to update from a response that has no content.

Christian Legnitto (1):
      Handle null for collection properties in response

Steve Cook (1):
      More liberal parsing of datetime timestamps

franck (1):
      Update requirements.txt

franck cuny (1):
      Fix broken http test for bad encoding.

1.2.1 (2012-05-21)
------------------

No changes entry was prepared, but here's the git shortlog since the last entry in here:

Brad Choate (3):
      Merge branch 'master' of github.com:sixapart/remoteobjects
      Allow dataobject to be iterable and adding a get method.
      Assign SequenceProxy class ahead of PromiseObject for PageObject so we prefer to iterate over the "entries" member.

Carl Meyer (8):
      PromiseObject.get() passes on kwargs to get_request() on delivery.
      Added test check for .get() passing on kwargs to .get_request().
      Added failing test for Link forwards-reference support.
      Extended string forwards-reference support to Link as well as Object.
      Don't try to update from a response that has no content.
      Merge branch 'master' into no-content-response
      Added test for correctly handling no-content success response.
      Merge branch 'master' into link-accepts-string-cls

Chris Adams (1):
      dataobject: fixed broken import in docstring

Mark Paschal (4):
      Honor location_header_required when filling the _location from the response too
      Nice up these configurations
      Expect 202 Accepted responses sometimes
      Accepted responses don't really have content

Martin Atkins (7):
      Fix issue that prevented fields from being unset.
      Test added in cdc40aa didn't actually test for the right case.
      Don't try to encode Nones.
      Merge pull request #8 from carljm/promise-kwargs
      Merge pull request #13 from carljm/no-content-response
      Merge pull request #11 from carljm/link-accepts-string-cls
      Update setup.py for new release.

Ross McFarland (5):
      simple utc class and use of it in remote objects
      handle UTC timezone's in encode
      handle encode of Datetime's with tzinfo's
      correct tzinfo comment per mart's cr comment.
      provide a simple UTC tz for working with dates

1.1.1 (2010-07-08)
------------------

* Applied a patch from Alex Gaynor to allow `None` for `Datetime` fields.


1.1 (2009-11-24)
----------------

* Added support for HEAD and OPTIONS request methods.
* Added some example client implementations (Netflix, Twitter, Giant Bomb, CouchDB)

1.0 (2009-09-30)
----------------

* Initial release.
