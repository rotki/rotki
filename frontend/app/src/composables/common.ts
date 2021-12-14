import { computed, getCurrentInstance } from '@vue/composition-api';
import { Section, Status } from '@/store/const';
import { Message } from '@/store/types';
import { useStore } from '@/store/utils';
import { assert } from '@/utils/assertions';

export const useProxy = () => {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  return currentInstance.proxy;
};

export const useRouter = () => {
  const { $router } = useProxy();
  return $router;
};

export const useRoute = () => {
  const { $router } = useProxy();
  return computed(() => $router.currentRoute);
};

export const setupThemeCheck = () => {
  const { $vuetify } = useProxy();
  const isMobile = computed(() => $vuetify.breakpoint.mobile);
  const dark = computed(() => $vuetify.theme.dark);
  const breakpoint = computed(() => $vuetify.breakpoint.name);
  const currentBreakpoint = computed(() => $vuetify.breakpoint);
  const width = computed(() => $vuetify.breakpoint.width);
  const fontStyle = computed(() => {
    return {
      color: dark.value ? 'rgba(255,255,255,0.87)' : 'rgba(0,0,0,0.87)'
    };
  });
  return {
    isMobile,
    dark,
    breakpoint,
    currentBreakpoint,
    width,
    fontStyle
  };
};

export const setupStatusChecking = () => {
  const store = useStore();

  const isSectionRefreshing = (section: Section) =>
    computed(() => {
      const status = store.getters['status'](section);
      return (
        status === Status.LOADING ||
        status === Status.REFRESHING ||
        status === Status.PARTIALLY_LOADED
      );
    });

  const shouldShowLoadingScreen = (section: Section) => {
    return computed(() => {
      const status = store.getters['status'](section);
      return (
        status !== Status.LOADED &&
        status !== Status.PARTIALLY_LOADED &&
        status !== Status.REFRESHING
      );
    });
  };
  return {
    isSectionRefreshing,
    shouldShowLoadingScreen
  };
};

export const isSectionLoading = (section: Section) => {
  const store = useStore();
  return computed(() => {
    const status = store.getters['status'](section);
    return status !== Status.LOADED && status !== Status.PARTIALLY_LOADED;
  });
};

export const setupMessages = () => {
  const store = useStore();
  const setMessage = async (message: Message) => {
    await store.dispatch('setMessage', message);
  };
  return {
    setMessage
  };
};
