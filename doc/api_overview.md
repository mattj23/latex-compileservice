# API Overview

As seen from the client side, the API offers access to a single main resource: an ephemeral "session".

Sessions are created by clients who want to compile a set of LaTeX source files into a single document, typically a PDF.  The client specifies a compiler and a target, posts a set of source files which may include Jinja2 templates and json objects to be rendered into source files, and then posts a "ready" flag which prevents futher alterations to the session.

Once the session is marked as "ready", a background worker will eventually pick it up, after which time it will either be successfully compiled into a document, or the compilation will fail.  The session state will change to either "finished" or "error".

At that point, the session will contain a link to log files, and (if it completed successfully) a product, which the client may download.

The session will only persist for a limited amount of time (set by the server) after completion.  It is the responsibility of the client to check and download the results before the session is removed.