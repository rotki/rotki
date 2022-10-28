import { getStatus, useStatusStore } from '@/store/status';
import { Section, Status } from '@/types/status';
import { assert } from '@/utils/assertions';

export const useProxy = () => {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  return currentInstance.proxy;
};

export const useTheme = () => {
  const { $vuetify } = useProxy();
  const isMobile = computed(() => $vuetify.breakpoint.mobile);
  const theme = computed(() => $vuetify.theme);
  const dark = computed(() => $vuetify.theme.dark);
  const breakpoint = computed(() => $vuetify.breakpoint.name);
  const currentBreakpoint = computed(() => $vuetify.breakpoint);
  const width = computed(() => $vuetify.breakpoint.width);
  const fontStyle = computed(() => {
    return {
      color: get(dark) ? 'rgba(255,255,255,0.87)' : 'rgba(0,0,0,0.87)'
    };
  });
  const appBarColor = computed(() => {
    if (!get(dark)) {
      return 'white';
    }
    return null;
  });
  return {
    $vuetify,
    isMobile,
    theme,
    dark,
    breakpoint,
    currentBreakpoint,
    width,
    fontStyle,
    appBarColor
  };
};

export const useSectionLoading = () => {
  const { getStatus } = useStatusStore();
  const isSectionRefreshing = (section: Section) => {
    const sectionStatus = getStatus(section);
    return computed(() => {
      const status = get(sectionStatus);
      return (
        status === Status.LOADING ||
        status === Status.REFRESHING ||
        status === Status.PARTIALLY_LOADED
      );
    });
  };

  const shouldShowLoadingScreen = (section: Section) => {
    const sectionStatus = getStatus(section);
    return computed(() => {
      const status = get(sectionStatus);
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
  return computed(() => {
    const status = getStatus(section);
    return status !== Status.LOADED && status !== Status.PARTIALLY_LOADED;
  });
};
