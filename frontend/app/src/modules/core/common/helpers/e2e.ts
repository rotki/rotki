/**
 * Creates a polyfill of ResizeObserver to work around some crashes when running e2e tests.
 * for more information check: https://github.com/cypress-io/cypress/issues/27415#issuecomment-2169155274
 * make sure to remove if the linked issue is resolved.
 */
export function attemptPolyfillResizeObserver(): void {
  if (!import.meta.env.VITE_E2E)
    return;

  console.warn('Using polyfill for ResizeObserver because of VITE_E2E being set');

  const RealResizeObserver = ResizeObserver;

  let queueFlushTimeout: number | undefined;
  let queue: { cb: ResizeObserverCallback; args: ResizeObserverEntry[] }[] = [];

  /**
   * ResizeObserver wrapper with "enforced batches"
   */
  class ResizeObserverPolyfill {
    private readonly callback: ResizeObserverCallback;
    private readonly observer: ResizeObserver;

    constructor(callback: ResizeObserverCallback) {
      this.callback = callback;
      this.observer = new RealResizeObserver(this.check.bind(this));
    }

    observe(element: Element): void {
      this.observer.observe(element);
    }

    unobserve(element: Element): void {
      this.observer.unobserve(element);
    }

    disconnect(): void {
      this.observer.disconnect();
    }

    /**
     * Queues one pending call per callback, flushed together on the next frame.
     *
     * @remarks
     * Replacing this callback's queue entry rather than appending is what enforces the batch: only
     * the latest entries for a given callback survive to the flush, so a burst of resizes cannot
     * re-enter the observer and raise the loop-limit error this polyfill exists to avoid.
     */
    check(entries: ResizeObserverEntry[]): void {
      queue = queue.filter(x => x.cb !== this.callback);
      queue.push({ args: entries, cb: this.callback });
      queueFlushTimeout ??= requestAnimationFrame(() => {
        queueFlushTimeout = undefined;
        const q = queue;
        queue = [];
        q.forEach(({ args, cb }) => cb(args, this.observer));
      });
    }
  }

  window.ResizeObserver = ResizeObserverPolyfill;
}
