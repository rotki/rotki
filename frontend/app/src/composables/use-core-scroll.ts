export function useCoreScroll() {
  const { y: scrollY } = useScroll(document.body);

  const shouldShowScrollToTopButton = computed<boolean>(() => get(scrollY) > 200);

  function scrollToTop(): void {
    document.body.scrollTo(0, 0);
  }

  return {
    scrollToTop,
    shouldShowScrollToTopButton,
  };
}
