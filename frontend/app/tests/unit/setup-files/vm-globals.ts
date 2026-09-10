import { BroadcastChannel as NodeBroadcastChannel } from 'node:worker_threads';

/*
 * A `vmThreads` worker evaluates each test file in a fresh V8 context, and that context carries
 * the environment's globals rather than Node's. `BroadcastChannel` is not among them, so MSW,
 * which reaches for it at import time, throws `ReferenceError` before any test runs. See
 * https://github.com/mswjs/msw/issues/2340.
 *
 * This file is listed ahead of `setup.ts` in `setupFiles` so the global exists before the MSW
 * server module is evaluated. Under a pool that already provides it the branch is skipped.
 *
 * `Reflect.set` rather than assignment: node's channel and the DOM lib's declaration describe the
 * same runtime object with different constructor types, and this keeps the seam free of a cast.
 */
if (!('BroadcastChannel' in globalThis))
  Reflect.set(globalThis, 'BroadcastChannel', NodeBroadcastChannel);
