import { computed, getCurrentInstance } from '@vue/composition-api';
import { assert } from '@/utils/assertions';

export const useProxy = () => {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  return currentInstance.proxy;
};

export const setupThemeCheck = () => {
  const { $vuetify } = useProxy();
  const isMobile = computed(() => $vuetify.breakpoint.mobile);
  const dark = computed(() => $vuetify.theme.dark);
  return {
    isMobile,
    dark
  };
};
