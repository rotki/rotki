import type { MaybeRef } from '@vueuse/core';

interface UseLinksReturn {
  href: ComputedRef<string | undefined>;
  hasLink: ComputedRef<boolean>;
  linkTarget: ComputedRef<'_blank' | undefined>;
  onLinkClick: () => void;
}

export function useLinks(url?: MaybeRef<string | undefined>): UseLinksReturn {
  const { isPackaged, openUrl } = useInterop();
  const targetUrl = computed(() => get(url) ?? externalLinks.premium);
  const href = computed(() => (isPackaged ? undefined : get(targetUrl)));

  const linkTarget = computed<'_blank' | undefined>(() => (isPackaged ? undefined : '_blank'));

  const onLinkClick = !isPackaged
    ? (): void => {}
    : (): void => {
        openUrl(get(targetUrl));
      };

  const hasLink = computed<boolean>(() => get(url)?.startsWith('http') ?? false);

  return {
    href,
    hasLink,
    linkTarget,
    onLinkClick,
  };
}
