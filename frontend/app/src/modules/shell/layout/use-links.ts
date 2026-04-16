import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { externalLinks } from '@shared/external-links';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseLinksReturn {
  href: ComputedRef<string | undefined>;
  hasLink: ComputedRef<boolean>;
  linkTarget: ComputedRef<'_blank' | undefined>;
  onLinkClick: () => void;
}

export function useLinks(url?: MaybeRefOrGetter<string | undefined>): UseLinksReturn {
  const { isPackaged, openUrl } = useInterop();
  const targetUrl = computed(() => toValue(url) ?? externalLinks.premium);
  const href = computed(() => (isPackaged ? undefined : get(targetUrl)));

  const linkTarget = computed<'_blank' | undefined>(() => (isPackaged ? undefined : '_blank'));

  const onLinkClick = !isPackaged
    ? (): void => {}
    : async (): Promise<void> => {
      await openUrl(get(targetUrl));
    };

  const hasLink = computed<boolean>(() => toValue(url)?.startsWith('http') ?? false);

  return {
    hasLink,
    href,
    linkTarget,
    onLinkClick,
  };
}
