import type { ComputedRef } from 'vue';

interface UseScrollReturn {
  scrollToTop: () => void;
  shouldShowScrollToTopButton: ComputedRef<boolean>;
}

export function useCoreScroll(): UseScrollReturn {
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
