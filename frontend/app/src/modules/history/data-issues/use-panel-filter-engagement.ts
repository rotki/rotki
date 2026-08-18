import type { MaybeElementRef } from '@vueuse/core';
import type { Ref } from 'vue';

/**
 * How long after focus leaves the filter the panel keeps treating it as engaged.
 * Long enough to cover the trailing click on a teleported suggestion, which fires
 * after the input blurs.
 */
const DISENGAGE_DELAY = 300;

/**
 * Whether the user is currently interacting with the panel's filter.
 *
 * The filter's suggestion dropdown is a `RuiMenu` teleported to `<body>`, so clicking
 * a suggestion (an asset, say) reads as a click outside the floating drawer and would
 * dismiss it. The host drawer stays stateless while this is true, and it is held for a
 * short grace period after focus leaves so that trailing click is still ignored.
 */
export function usePanelFilterEngagement(target: MaybeElementRef): Readonly<Ref<boolean>> {
  const { focused } = useFocusWithin(target);
  const engaged = shallowRef<boolean>(false);

  const { start: scheduleDisengage, stop: cancelDisengage } = useTimeoutFn(() => {
    set(engaged, false);
  }, DISENGAGE_DELAY, { immediate: false });

  watch(focused, (isFocused) => {
    if (isFocused) {
      cancelDisengage();
      set(engaged, true);
    }
    else {
      scheduleDisengage();
    }
  });

  return readonly(engaged);
}
