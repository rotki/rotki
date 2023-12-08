export const useLinks = (url?: Ref<string | undefined>) => {
  const { isPackaged, premiumURL, openUrl } = useInterop();
  const targetUrl = computed(() => get(url) ?? premiumURL);
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
    onLinkClick
  };
};
