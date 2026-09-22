"""Offline main-loop/thread-boundary checks; run GTK tests under xvfb-run."""

from threading import Event, get_ident
from time import monotonic, sleep

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from samfunnsdata.gui_jobs import GuiJobs

pytestmark = pytest.mark.skipif(
    not Gtk.init_check(), reason="GTK display required (use xvfb-run)"
)


def pump_until(predicate, timeout=5):
    context = GLib.MainContext.default()
    deadline = monotonic() + timeout
    while not predicate():
        assert monotonic() < deadline, "Timed out waiting for GTK job"
        context.iteration(False)
        sleep(0.001)
    while context.pending():
        context.iteration(False)


def test_responsive_main_loop_and_thread_delivery():
    owner = get_ident()
    started, release, second_event = Event(), Event(), Event()
    label = Gtk.Label()
    calls, busy, errors = [], [], []
    jobs = GuiJobs(busy.append, errors.append)

    def work(token):
        calls.append(("worker", get_ident()))
        started.set()
        assert release.wait(4)
        return "completed"

    def apply(value):
        calls.append(("apply", get_ident()))
        label.set_text(value)

    try:
        jobs.submit(work, apply)
        pump_until(started.is_set)

        def another_event():
            assert jobs.active
            label.set_text("another UI event")
            second_event.set()
            return GLib.SOURCE_REMOVE

        GLib.idle_add(another_event)
        # Deliberate 1.2-second fake request. The GTK timer releases the worker.
        GLib.timeout_add(1200, lambda: (release.set(), GLib.SOURCE_REMOVE)[1])
        pump_until(second_event.is_set)
        assert label.get_text() == "another UI event"
        assert busy == [True]
        pump_until(lambda: not jobs.active)
        assert label.get_text() == "completed"
        assert calls[0][1] != owner
        assert calls[1] == ("apply", owner)
        assert busy == [True, False] and errors == []
    finally:
        release.set()
        jobs.close()
        pump_until(lambda: jobs.outstanding == 0)


@pytest.mark.parametrize("old_error", [False, True])
def test_newest_success_wins_when_old_finishes_last(old_error):
    a_started, b_started, release_a, release_b = (Event() for _ in range(4))
    applied, errors, busy = [], [], []
    jobs = GuiJobs(busy.append, errors.append)

    def a(token):
        a_started.set()
        assert release_a.wait(5)
        if old_error:
            raise ValueError("stale error")
        return "A/chart A"

    def b(token):
        b_started.set()
        assert release_b.wait(5)
        return "B/chart B"

    try:
        jobs.submit(a, applied.append)
        pump_until(a_started.is_set)
        jobs.submit(b, applied.append)
        pump_until(b_started.is_set)
        release_b.set()
        pump_until(lambda: applied == ["B/chart B"])
        assert not jobs.active
        release_a.set()
        pump_until(lambda: jobs.outstanding == 0)
        assert applied == ["B/chart B"] and errors == []
        assert busy == [True, True, False]
    finally:
        release_a.set()
        release_b.set()
        jobs.close()
        pump_until(lambda: jobs.outstanding == 0)


def test_worker_and_queue_bound_with_many_requests():
    started = [Event(), Event()]
    release = Event()
    ran, applied = [], []
    jobs = GuiJobs(lambda _: None, pytest.fail)

    def blocked(number):
        def work(token):
            ran.append((number, get_ident()))
            started[number].set()
            assert release.wait(5)
            return number

        return work

    try:
        for i in range(2):
            jobs.submit(blocked(i), applied.append)
            pump_until(started[i].is_set)
        for number in range(2, 102):

            def work(token, number=number):
                ran.append((number, get_ident()))
                return number

            jobs.submit(work, applied.append)
            assert jobs.outstanding == 3
        release.set()
        pump_until(lambda: not jobs.active and jobs.outstanding == 0)
        assert applied == [101]
        assert sorted(number for number, _ in ran) == [0, 1, 101]
        assert len({thread for _, thread in ran}) <= jobs.worker_limit == 2
    finally:
        release.set()
        jobs.close()
        pump_until(lambda: jobs.outstanding == 0)


@pytest.mark.parametrize("action", ["cancel", "close"])
def test_cancel_and_close_prevent_late_delivery(action):
    started, release = Event(), Event()
    applied, errors, busy = [], [], []
    jobs = GuiJobs(busy.append, errors.append)

    def work(token):
        started.set()
        assert release.wait(5)
        token.checkpoint()
        return "late"

    try:
        jobs.submit(work, applied.append)
        pump_until(started.is_set)
        getattr(jobs, action)()
        release.set()
        pump_until(lambda: jobs.outstanding == 0)
        assert not jobs.active
        assert applied == errors == []
        assert busy == ([True, False] if action == "cancel" else [True])
    finally:
        release.set()
        jobs.close()


@pytest.mark.parametrize("apply_error", [False, True])
def test_active_error_clears_busy_and_next_request_works(apply_error):
    errors, busy, applied = [], [], []
    jobs = GuiJobs(busy.append, errors.append)

    def fail(*_args):
        raise ValueError("Lesbar feil")

    try:
        jobs.submit(
            (lambda token: 1) if apply_error else fail,
            fail if apply_error else applied.append,
        )
        pump_until(lambda: not jobs.active)
        assert errors == ["Lesbar feil"] and busy == [True, False]
        jobs.submit(lambda token: "recovered", applied.append)
        pump_until(lambda: not jobs.active)
        assert applied == ["recovered"]
    finally:
        jobs.close()
