"""Auto-logging decorator for halctl commands.

Every halctl command wrapped with @logged emits an hlog entry
before returning, so logctl picks up all fleet admin actions.
"""

import functools

from halos.common.log import hlog


def logged(func):
    """Decorator: emit hlog("halctl", ...) for every command invocation."""

    @functools.wraps(func)
    def wrapper(args, *extra, **kwargs):
        cmd_name = func.__name__.removeprefix("cmd_")
        instance = getattr(args, "name", None)

        try:
            rc = func(args, *extra, **kwargs)
            level = "error" if rc and rc != 0 else "info"
            hlog("halctl", level, cmd_name, {
                "instance": instance,
                "exit": rc or 0,
            })
            return rc
        except Exception as exc:
            hlog("halctl", "error", cmd_name, {
                "instance": instance,
                "error": str(exc),
            })
            raise

    return wrapper
