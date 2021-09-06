import { computed, getCurrentInstance } from '@vue/composition-api';
import { assert } from '@/utils/assertions';

export const setupThemeCheck = () => {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  const { $vuetify } = currentInstance.proxy;
  const isMobile = computed(() => $vuetify.breakpoint.mobile);
  const dark = computed(() => $vuetify.theme.dark);
  return {
    isMobile,
    dark
  };
};
