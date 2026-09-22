"""Bounded GUI jobs. Scheduling and delivery belong to the creating thread."""

from concurrent.futures import CancelledError, ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Event, get_ident

from gi.repository import GLib


@dataclass
class JobToken:
    generation: int
    cancelled: Event = field(default_factory=Event)

    def checkpoint(self):
        if self.cancelled.is_set():
            raise CancelledError()


class GuiJobs:
    """At most two submitted jobs and one replaceable pending request per window.

    Never fill ThreadPoolExecutor's unbounded internal queue. Superseded running
    calls may finish (provider timeouts still apply), but cannot deliver results.
    """

    worker_limit = 2

    def __init__(self, busy, error):
        self._owner = get_ident()
        self._busy = busy
        self._error = error
        self._executor = ThreadPoolExecutor(
            max_workers=self.worker_limit, thread_name_prefix="samfunnsdata-gui"
        )
        self._running = {}
        self._pending = None
        self.generation = 0
        self.closed = False
        self.active = False

    def _assert_owner(self):
        if get_ident() != self._owner:
            raise RuntimeError("GUI job scheduling/delivery requires the GTK thread")

    @property
    def outstanding(self):
        return len(self._running) + (self._pending is not None)

    def _invalidate(self):
        self.generation += 1
        for token in self._running.values():
            token.cancelled.set()
        if self._pending:
            self._pending[0].cancelled.set()
        self._pending = None

    def submit(self, work, apply):
        self._assert_owner()
        if self.closed:
            return
        self._invalidate()
        token = JobToken(self.generation)
        self.active = True
        self._busy(True)
        request = (token, work, apply)
        if len(self._running) < self.worker_limit:
            self._start(request)
        else:
            self._pending = request
        return token.generation

    def _start(self, request):
        token, work, apply = request

        def run():
            token.checkpoint()
            return work(token)

        future = self._executor.submit(run)
        self._running[future] = token
        future.add_done_callback(
            lambda done: GLib.idle_add(self._finish, done, token, apply)
        )

    def _finish(self, future, token, apply):
        self._assert_owner()
        self._running.pop(future, None)
        if self.closed:
            return GLib.SOURCE_REMOVE
        if self._pending:
            request, self._pending = self._pending, None
            self._start(request)
        if token.generation != self.generation or token.cancelled.is_set():
            return GLib.SOURCE_REMOVE
        try:
            apply(future.result())
        except CancelledError:
            pass
        except Exception as error:  # noqa: BLE001
            self._error(str(error))
        finally:
            # An apply callback may itself submit another request.
            if token.generation == self.generation and not self.closed:
                self.active = False
                self._busy(False)
        return GLib.SOURCE_REMOVE

    def cancel(self):
        self._assert_owner()
        if self.closed:
            return
        self._invalidate()
        self.active = False
        self._busy(False)

    def close(self):
        self._assert_owner()
        if self.closed:
            return
        self._invalidate()
        self.closed = True
        self.active = False
        # Do not touch widgets, wait for HTTP, or claim running calls are aborted.
        self._busy = self._error = None
        self._executor.shutdown(wait=False, cancel_futures=True)
