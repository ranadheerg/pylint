`Pylint`_
=========

.. _`Pylint`: https://pylint.readthedocs.io/

.. This is used inside the doc to recover the start of the introduction

.. image:: https://github.com/pylint-dev/pylint/actions/workflows/tests.yaml/badge.svg?branch=main
    :target: https://github.com/pylint-dev/pylint/actions

.. image:: https://codecov.io/gh/pylint-dev/pylint/branch/main/graph/badge.svg?token=ZETEzayrfk
    :target: https://codecov.io/gh/pylint-dev/pylint

.. image:: https://img.shields.io/pypi/v/pylint.svg
    :alt: PyPI Package version
    :target: https://pypi.python.org/pypi/pylint

.. image:: https://readthedocs.org/projects/pylint/badge/?version=latest
    :target: https://pylint.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

.. image:: https://img.shields.io/badge/linting-pylint-yellowgreen
    :target: https://github.com/pylint-dev/pylint

.. image:: https://results.pre-commit.ci/badge/github/pylint-dev/pylint/main.svg
   :target: https://results.pre-commit.ci/latest/github/pylint-dev/pylint/main
   :alt: pre-commit.ci status

.. image:: https://bestpractices.coreinfrastructure.org/projects/6328/badge
   :target: https://bestpractices.coreinfrastructure.org/projects/6328
   :alt: CII Best Practices

.. image:: https://img.shields.io/ossf-scorecard/github.com/PyCQA/pylint?label=openssf%20scorecard&style=flat
   :target: https://api.securityscorecards.dev/projects/github.com/PyCQA/pylint
   :alt: OpenSSF Scorecard

.. image:: https://img.shields.io/discord/825463413634891776.svg
   :target: https://discord.gg/qYxpadCgkx
   :alt: Discord

What is Pylint?
---------------

Pylint is a `static code analyser`_ for Python 2 or 3. The latest version supports Python
3.10.0 and above.

.. _`static code analyser`: https://en.wikipedia.org/wiki/Static_code_analysis

Pylint analyses your code without actually running it. It checks for errors, enforces a
coding standard, looks for `code smells`_, and can make suggestions about how the code
could be refactored.

.. _`code smells`: https://martinfowler.com/bliki/CodeSmell.html

Install
-------

.. This is used inside the doc to recover the start of the short text for installation

For command line use, pylint is installed with::

    pip install pylint

Or if you want to also check spelling with ``enchant`` (you might need to
`install the enchant C library <https://pyenchant.github.io/pyenchant/install.html#installing-the-enchant-c-library>`_):

.. code-block:: sh

   pip install pylint[spelling]

It can also be integrated in most editors or IDEs. More information can be found
`in the documentation`_.

.. _in the documentation: https://pylint.readthedocs.io/en/latest/user_guide/installation/index.html

.. This is used inside the doc to recover the end of the short text for installation

What differentiates Pylint?
---------------------------

Pylint is not trusting your typing and is inferring the actual values of nodes (for a
start because there was no typing when pylint started off) using its internal code
representation (astroid). If your code is ``import logging as argparse``, Pylint
can check and know that ``argparse.error(...)`` is in fact a logging call and not an
argparse call. This makes pylint slower, but it also lets pylint find more issues if
your code is not fully typed.

    [inference] is the killer feature that keeps us using [pylint] in our project despite how painfully slow it is.
    - `Realist pylint user`_, 2022

.. _`Realist pylint user`: https://github.com/charliermarsh/ruff/issues/970#issuecomment-1381067064

pylint, not afraid of being a little slower than it already is, is also a lot more thorough than other linters.
There are more checks, including some opinionated ones that are deactivated by default
but can be enabled using configuration.

How to use pylint
-----------------

Pylint isn't smarter than you: it may warn you about things that you have
conscientiously done or check for some things that you don't care about.
During adoption, especially in a legacy project where pylint was never enforced,
it's best to start with the ``--errors-only`` flag, then disable
convention and refactor messages with ``--disable=C,R`` and progressively
re-evaluate and re-enable messages as your priorities evolve.

Pylint is highly configurable and permits to write plugins in order to add your
own checks (for example, for internal libraries or an internal rule). Pylint also has an
ecosystem of existing plugins for popular frameworks and third-party libraries.

.. note::

    Pylint supports the Python standard library out of the box. Third-party
    libraries are not always supported, so a plugin might be needed. A good place
    to start is ``PyPI`` which often returns a plugin by searching for
    ``pylint <library>``. `pylint-pydantic`_, `pylint-django`_ and
    `pylint-sonarjson`_ are examples of such plugins. More information about plugins
    and how to load them can be found at `plugins`_.

.. _`plugins`: https://pylint.readthedocs.io/en/latest/development_guide/how_tos/plugins.html#plugins
.. _`pylint-pydantic`: https://pypi.org/project/pylint-pydantic
.. _`pylint-django`: https://github.com/pylint-dev/pylint-django
.. _`pylint-sonarjson`: https://github.com/cnescatlab/pylint-sonarjson-catlab

Advised linters alongside pylint
--------------------------------

Projects that you might want to use alongside pylint include ruff_ (**really** fast,
with builtin auto-fix and a large number of checks taken from popular linters, but
implemented in ``rust``) or flake8_ (a framework to implement your own checks in python using ``ast`` directly),
mypy_, pyright_ / pylance or pyre_ (typing checks), bandit_ (security oriented checks), black_ and
isort_ (auto-formatting), autoflake_ (automated removal of unused imports or variables), pyupgrade_
(automated upgrade to newer python syntax) and pydocstringformatter_ (automated pep257).

.. _ruff: https://github.com/astral-sh/ruff
.. _flake8: https://github.com/PyCQA/flake8
.. _bandit: https://github.com/PyCQA/bandit
.. _mypy: https://github.com/python/mypy
.. _pyright: https://github.com/microsoft/pyright
.. _pyre: https://github.com/facebook/pyre-check
.. _black: https://github.com/psf/black
.. _autoflake: https://github.com/myint/autoflake
.. _pyupgrade: https://github.com/asottile/pyupgrade
.. _pydocstringformatter: https://github.com/DanielNoord/pydocstringformatter
.. _isort: https://pycqa.github.io/isort/

Additional tools included in pylint
-----------------------------------

Pylint ships with two additional tools:

- pyreverse_ (standalone tool that generates package and class diagrams.)
- symilar_  (duplicate code finder that is also integrated in pylint)

.. _pyreverse: https://pylint.readthedocs.io/en/latest/additional_tools/pyreverse/index.html
.. _symilar: https://pylint.readthedocs.io/en/latest/additional_tools/symilar/index.html


.. This is used inside the doc to recover the end of the introduction

Contributing
------------

.. This is used inside the doc to recover the start of the short text for contribution

We welcome all forms of contributions such as updates for documentation, new code, checking issues for duplicates or telling us
that we can close them, confirming that issues still exist, `creating issues because
you found a bug or want a feature`_, etc. Everything is much appreciated!

Please follow the `code of conduct`_ and check `the Contributor Guides`_ if you want to
make a code contribution.

.. _creating issues because you found a bug or want a feature: https://pylint.readthedocs.io/en/latest/contact.html#bug-reports-feedback
.. _code of conduct: https://github.com/pylint-dev/pylint/blob/main/CODE_OF_CONDUCT.md
.. _the Contributor Guides: https://pylint.readthedocs.io/en/latest/development_guide/contribute.html

.. This is used inside the doc to recover the end of the short text for contribution

Show your usage
-----------------

You can place this badge in your README to let others know your project uses pylint.

    .. image:: https://img.shields.io/badge/linting-pylint-yellowgreen
        :target: https://github.com/pylint-dev/pylint

Learn how to add a badge to your documentation in `the badge documentation`_.

.. _the badge documentation: https://pylint.readthedocs.io/en/latest/user_guide/installation/badge.html

License
-------

pylint is, with a few exceptions listed below, `GPLv2 <https://github.com/pylint-dev/pylint/blob/main/LICENSE>`_.

The icon files are licensed under the `CC BY-SA 4.0 <https://creativecommons.org/licenses/by-sa/4.0/>`_ license:

- `doc/logo.png <https://raw.githubusercontent.com/pylint-dev/pylint/main/doc/logo.png>`_
- `doc/logo.svg <https://raw.githubusercontent.com/pylint-dev/pylint/main/doc/logo.svg>`_

Support
-------

Please check `the contact information`_.

.. _`the contact information`: https://pylint.readthedocs.io/en/latest/contact.html

.. |tideliftlogo| image:: https://raw.githubusercontent.com/pylint-dev/pylint/main/doc/media/Tidelift_Logos_RGB_Tidelift_Shorthand_On-White.png
   :width: 200
   :alt: Tidelift

.. list-table::
   :widths: 10 100

   * - |tideliftlogo|
     - Professional support for pylint is available as part of the `Tidelift
       Subscription`_.  Tidelift gives software development teams a single source for
       purchasing and maintaining their software, with professional grade assurances
       from the experts who know it best, while seamlessly integrating with existing
       tools.

.. _Tidelift Subscription: https://tidelift.com/subscription/pkg/pypi-pylint?utm_source=pypi-pylint&utm_medium=referral&utm_campaign=readme
