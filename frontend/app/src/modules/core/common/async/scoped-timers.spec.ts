import { get, set } from '@vueuse/shared';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, nextTick, ref } from 'vue';
import {
  refDebounced,
  refThrottled,
  useDebounceFn,
  useThrottleFn,
  watchDebounced,
  watchThrottled,
} from '@/modules/core/common/async/scoped-timers';

describe('modules/core/common/async/scoped-timers', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('useDebounceFn', () => {
    it('should run after the delay while its scope lives', async () => {
      const fn = vi.fn();
      const scope = effectScope();
      const debounced = scope.run(() => useDebounceFn(fn, 100))!;

      startPromiseIgnored(debounced('a'));
      startPromiseIgnored(debounced('b'));
      await vi.advanceTimersByTimeAsync(100);

      expect(fn).toHaveBeenCalledExactlyOnceWith('b');
      scope.stop();
    });

    it('should drop a pending call when its scope is disposed', async () => {
      const fn = vi.fn();
      const scope = effectScope();
      const debounced = scope.run(() => useDebounceFn(fn, 100))!;

      startPromiseIgnored(debounced());
      scope.stop();
      await vi.advanceTimersByTimeAsync(100);

      expect(fn).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(0);
    });

    it('should keep cancel and flush', async () => {
      const fn = vi.fn();
      const debounced = useDebounceFn(fn, 100);

      startPromiseIgnored(debounced());
      debounced.cancel();
      await vi.advanceTimersByTimeAsync(100);
      expect(fn).not.toHaveBeenCalled();

      startPromiseIgnored(debounced());
      debounced.flush();
      expect(fn).toHaveBeenCalledOnce();
    });

    it('should behave like VueUse outside an effect scope', async () => {
      const fn = vi.fn();
      const debounced = useDebounceFn(fn, 100);

      startPromiseIgnored(debounced());
      await vi.advanceTimersByTimeAsync(100);

      expect(fn).toHaveBeenCalledOnce();
    });
  });

  describe('useThrottleFn', () => {
    it('should drop a trailing call when its scope is disposed', async () => {
      const fn = vi.fn();
      const scope = effectScope();
      const throttled = scope.run(() => useThrottleFn(fn, 100))!;

      startPromiseIgnored(throttled('leading'));
      startPromiseIgnored(throttled('trailing'));
      scope.stop();
      await vi.advanceTimersByTimeAsync(100);

      expect(fn).toHaveBeenCalledExactlyOnceWith('leading');
    });
  });

  describe('watchDebounced', () => {
    it('should not run the callback for a change still pending when its scope is disposed', async () => {
      const source = ref(0);
      const cb = vi.fn();
      const scope = effectScope();
      scope.run(() => watchDebounced(source, cb, { debounce: 100 }));

      set(source, 1);
      await nextTick();
      scope.stop();
      await vi.advanceTimersByTimeAsync(100);

      expect(cb).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(0);
    });

    it('should run the callback after the delay while its scope lives', async () => {
      const source = ref(0);
      const cb = vi.fn();
      const scope = effectScope();
      scope.run(() => watchDebounced(source, cb, { debounce: 100 }));

      set(source, 1);
      await nextTick();
      await vi.advanceTimersByTimeAsync(100);

      expect(cb).toHaveBeenCalledOnce();
      scope.stop();
    });
  });

  describe('watchThrottled', () => {
    it('should not run a trailing callback after its scope is disposed', async () => {
      const source = ref(0);
      const cb = vi.fn();
      const scope = effectScope();
      scope.run(() => watchThrottled(source, cb, { throttle: 100 }));

      set(source, 1);
      await nextTick();
      set(source, 2);
      await nextTick();
      scope.stop();
      await vi.advanceTimersByTimeAsync(100);

      expect(cb).toHaveBeenCalledOnce();
    });
  });

  describe('refDebounced', () => {
    it('should follow the source after the delay and stop with its scope', async () => {
      const source = ref('a');
      const scope = effectScope();
      const debounced = scope.run(() => refDebounced(source, 100))!;

      set(source, 'b');
      await nextTick();
      await vi.advanceTimersByTimeAsync(100);
      expect(get(debounced)).toBe('b');

      set(source, 'c');
      await nextTick();
      scope.stop();
      await vi.advanceTimersByTimeAsync(100);
      expect(get(debounced)).toBe('b');
    });
  });

  describe('refThrottled', () => {
    it('should follow the source and drop a trailing update after its scope is disposed', async () => {
      const source = ref('a');
      const scope = effectScope();
      const throttled = scope.run(() => refThrottled(source, 100))!;

      set(source, 'b');
      await nextTick();
      expect(get(throttled)).toBe('b');

      set(source, 'c');
      await nextTick();
      scope.stop();
      await vi.advanceTimersByTimeAsync(100);
      expect(get(throttled)).toBe('b');
    });
  });
});

/** The debounced and throttled calls return promises the specs settle through the timers. */
function startPromiseIgnored(promise: Promise<unknown>): void {
  promise.catch(() => {});
}
