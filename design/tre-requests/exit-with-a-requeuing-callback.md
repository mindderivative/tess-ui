# Request to tre: `run()` returns after the last window closes, even with a callback that re-queues itself

*Drafted for Tesserae 0.6.0 (#297). Sent 2026-11-03 as mindderivative/tess-re#260.*

## What Tesserae needs

`App.run(keepalive=True)` queues a callback that sleeps 20 ms and calls `thread_handle().call_soon` on itself again, so an idle window's loop keeps pumping and other Python threads get the GIL. When the window closes, `run()` must return, as it did in `tre` 0.5.8, whatever that callback does.

## What happens today (`tess_re` 0.6.0, macOS)

`run()` does not return after the last window closes while such a callback is queued. Linux returns.

Bisected on GitHub's macOS runners with `tests/test_keepalive_idle.py` (a real window, a worker thread that calls `call_soon` at 1 s and `app.close` at 2 s):

| engine | result |
|---|---|
| 0.5.8 | passes |
| 0.5.9 | hangs, killed at 60 s |
| 0.5.10 | hangs |
| 0.6.0 | hangs (also with `TESS_RE_GPU_DEVICES=per-window` and `TESS_RE_GPU_RENDERERS=per-window`) |

A `faulthandler` dump of the hung 0.6.0 process, 25 s in, after `app.close` was queued: the main thread is inside Tesserae's `tick`, called from `run()`. Without the keep-alive callback `run()` returns 0.05 s after the close. If Tesserae's callback stops re-queuing itself once the window's `closed` event fires, the same test passes on macOS (`run()` returns 2.3 s in).

## The mechanism, from reading the code (not run under a debugger)

0.5.9 (#238) added `LoopOptions::on_wake`, which runs the host's queued callbacks on every wake while no window or layer surface is open, and `exit_if_empty`, which calls `event_loop.exit()` when the last window is gone. `ThreadHandle::drain` takes a snapshot of the queue, but "after running anything, the loop is woken once more". A callback that queues itself therefore makes a chain: wake, `on_wake`, drain, the callback queues itself, wake, and so on, with no window open. On Linux the exit that `exit_if_empty` asked for wins; on macOS (winit 0.30) it appears not to while the chain keeps delivering events. **The winit half is an inference.**

## The ask

Once the loop has been asked to exit (`exit_if_empty` has called `event_loop.exit()`, or `Stop` has run), do not run `on_wake` or re-wake from `drain`, so that a callback that re-queues itself cannot keep `run()` from returning. Tesserae's own callback now stops, but any host callback of this kind (a hot-reload poller, an IDE thread's pump) will hang a macOS app the same way.

## What the workaround costs

Tesserae 0.6.0 stops its own `tick` and frame-count callbacks when the main window closes (one flag). It does nothing for a user's own self-queuing `call_soon`.

## Questions for tre

- Does winit on macOS finish `exit()` while user events keep arriving? A short test with a proxy event sent in a loop would show it.
- Should `ThreadHandle::drain` re-wake the loop at all when the loop is exiting?
- Is there an opt-out, or is stopping `on_wake` after the exit decision enough?
