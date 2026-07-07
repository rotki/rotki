import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref } from 'vue';
import { useHistoryEventsAutoFetch } from './use-history-events-auto-fetch';

const REFRESH_INTERVAL = 60_000;

function mountAutoFetch(shouldFetch: Ref<boolean>, fetchFunction: () => Promise<void>): VueWrapper {
  return mount(defineComponent({
    render: () => null,
    setup() {
      useHistoryEventsAutoFetch(shouldFetch, fetchFunction);
      return {};
    },
  }));
}

describe('useHistoryEventsAutoFetch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should call the fetch function on each interval while enabled', async () => {
    const fetchFunction = vi.fn().mockResolvedValue(undefined);
    const wrapper = mountAutoFetch(ref(true), fetchFunction);

    expect(fetchFunction).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(2);

    wrapper.unmount();
  });

  it('should skip a tick while a previous fetch is still in flight', async () => {
    let resolve: () => void = () => {};
    const fetchFunction = vi.fn().mockImplementation(async () => new Promise<void>((res) => {
      resolve = res;
    }));
    const wrapper = mountAutoFetch(ref(true), fetchFunction);

    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(1);

    // second tick fires while the first fetch is unresolved -> guarded
    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(1);

    // once the in-flight fetch resolves, the next tick runs again
    resolve();
    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(2);

    wrapper.unmount();
  });

  it('should pause and resume when the enabled flag toggles', async () => {
    const shouldFetch = ref<boolean>(true);
    const fetchFunction = vi.fn().mockResolvedValue(undefined);
    const wrapper = mountAutoFetch(shouldFetch, fetchFunction);

    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(1);

    set(shouldFetch, false);
    await nextTick();
    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL * 3);
    expect(fetchFunction).toHaveBeenCalledTimes(1); // paused

    set(shouldFetch, true);
    await nextTick();
    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(2); // resumed

    wrapper.unmount();
  });

  it('should stop fetching after the component unmounts', async () => {
    const fetchFunction = vi.fn().mockResolvedValue(undefined);
    const wrapper = mountAutoFetch(ref(true), fetchFunction);

    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL);
    expect(fetchFunction).toHaveBeenCalledTimes(1);

    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(REFRESH_INTERVAL * 3);
    expect(fetchFunction).toHaveBeenCalledTimes(1);
  });
});
