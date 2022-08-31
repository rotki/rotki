import { get } from '@vueuse/core';
import { computed, Ref } from 'vue';
import { useInterop } from '@/electron-interop';

export const useLinks = (url?: Ref<string>) => {
  const { isPackaged, premiumURL, openUrl } = useInterop();
  const targetUrl = computed(() => get(url) ?? premiumURL);
  const href = computed(() => {
    if (isPackaged) {
      return undefined;
    }
    return get(targetUrl);
  });

  const onLinkClick = isPackaged
    ? undefined
    : () => {
        openUrl(get(targetUrl));
      };

  return {
    href,
    onLinkClick
  };
};
