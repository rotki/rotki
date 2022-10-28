import { Ref } from 'vue';
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

  const onLinkClick = !isPackaged
    ? () => {}
    : () => {
        openUrl(get(targetUrl));
      };

  const hasLink = computed(() => {
    return get(url)?.startsWith('http');
  });

  return {
    href,
    hasLink,
    onLinkClick
  };
};
