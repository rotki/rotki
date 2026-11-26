import { BroadcastChannel as NodeBroadcastChannel } from 'node:worker_threads';

/*
 * A `vmThreads` worker runs each test file in a fresh V8 context that lacks `BroadcastChannel`,
 * so MSW throws `ReferenceError` on import (https://github.com/mswjs/msw/issues/2340). Listed
 * ahead of `setup.ts` in `setupFiles` so it runs first. `Reflect.set` avoids a cast: node's and
 * the DOM lib's constructor types differ.
 */
if (!('BroadcastChannel' in globalThis))
  Reflect.set(globalThis, 'BroadcastChannel', NodeBroadcastChannel);
