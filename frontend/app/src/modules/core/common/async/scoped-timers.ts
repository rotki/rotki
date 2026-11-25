/**
 * VueUse's debounce and throttle helpers, bound to the effect scope that creates them.
 *
 * @remarks
 * VueUse keeps a pending debounce or throttle on a plain timer that outlives the component or
 * composable scope. A call scheduled just before an unmount then fires afterwards, against a route,
 * store or request of whatever is current by then. These versions stop invoking once their scope is
 * disposed and cancel the pending timer where VueUse allows it.
 *
 * They keep the VueUse names and signatures, so a call site switches by changing only its import, and
 * lint rejects importing these names from VueUse. Outside an effect scope they behave like VueUse's.
 */
import {
  createFilterWrapper,
  debounceFilter,
  type EventFilter,
  throttleFilter,
  tryOnScopeDispose,
  type refDebounced as vueuseRefDebounced,
  type refThrottled as vueuseRefThrottled,
  type useDebounceFn as vueuseUseDebounceFn,
  type useThrottleFn as vueuseUseThrottleFn,
  type watchDebounced as vueuseWatchDebounced,
  type watchThrottled as vueuseWatchThrottled,
  watchWithFilter,
} from '@vueuse/core';
import { ref, shallowReadonly, shallowRef, toValue, watch } from 'vue';

/** An event filter that stops invoking, and cancels its pending timer, once the current scope ends. */
function scopedFilter<F extends EventFilter & { cancel?: () => void }>(filter: F): EventFilter {
  let active = true;
  tryOnScopeDispose(() => {
    active = false;
    filter.cancel?.();
  });
  return async (invoke, options) => filter(() => (active ? invoke() : undefined), options);
}

export const useDebounceFn: typeof vueuseUseDebounceFn = (fn, ms, options) => {
  const filter = debounceFilter(ms ?? 200, options);
  const wrapper = createFilterWrapper(scopedFilter(filter), fn);
  return Object.assign(wrapper, {
    cancel: filter.cancel,
    flush: filter.flush,
    isPending: filter.isPending,
  });
};

export const useThrottleFn: typeof vueuseUseThrottleFn = (fn, ms, trailing, leading, rejectOnCancel) =>
  createFilterWrapper(scopedFilter(throttleFilter(ms ?? 200, trailing, leading, rejectOnCancel)), fn);

export const watchDebounced: typeof vueuseWatchDebounced = (source: any, cb: any, options: any = {}) => {
  const { debounce = 0, maxWait = undefined, ...watchOptions } = options;
  return watchWithFilter(source, cb, {
    ...watchOptions,
    eventFilter: scopedFilter(debounceFilter(debounce, { maxWait })),
  });
};

export const watchThrottled: typeof vueuseWatchThrottled = (source: any, cb: any, options: any = {}) => {
  const { leading = true, throttle = 0, trailing = true, ...watchOptions } = options;
  return watchWithFilter(source, cb, {
    ...watchOptions,
    eventFilter: scopedFilter(throttleFilter(throttle, trailing, leading)),
  });
};

/** A shallow ref where VueUse uses a deep one: the value is replaced whole on every update. */
export const refDebounced: typeof vueuseRefDebounced = (value, ms, options) => {
  const debounced = shallowRef(toValue(value));
  const updater = useDebounceFn(() => {
    debounced.value = value.value;
  }, ms ?? 200, options);
  watch(value, async () => updater());
  return shallowReadonly(debounced);
};

export const refThrottled: typeof vueuseRefThrottled = (value, delay = 200, trailing = true, leading = true) => {
  if (delay <= 0)
    return value;
  const throttled = ref(toValue(value));
  const updater = useThrottleFn(() => {
    throttled.value = value.value;
  }, delay, trailing, leading);
  watch(value, async () => updater());
  return throttled;
};
