import { externalLinks } from '@/data/external-links';
import type { MaybeRef } from '@vueuse/core';

export function useLinks(url?: MaybeRef<string | undefined>) {
  const { isPackaged, openUrl } = useInterop();
  const targetUrl = computed(() => get(url) ?? externalLinks.premium);
  const href = computed(() => (isPackaged ? undefined : get(targetUrl)));

  const linkTarget = computed(() => (isPackaged ? undefined : '_blank'));

  const onLinkClick = !isPackaged
    ? () => {}
    : () => {
        openUrl(get(targetUrl));
      };

  const hasLink = computed(() => get(url)?.startsWith('http'));

  return {
    href,
    hasLink,
    linkTarget,
    onLinkClick,
  };
}
