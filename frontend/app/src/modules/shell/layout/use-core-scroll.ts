import type { ComputedRef } from 'vue';
import { defaultDocument } from '@vueuse/core';

interface UseScrollReturn {
  scrollToTop: () => void;
  shouldShowScrollToTopButton: ComputedRef<boolean>;
}

export function useCoreScroll(): UseScrollReturn {
  const { y: scrollY } = useScroll(defaultDocument?.body);

  const shouldShowScrollToTopButton = computed<boolean>(() => get(scrollY) > 200);

  function scrollToTop(): void {
    defaultDocument?.body.scrollTo(0, 0);
  }

  return {
    scrollToTop,
    shouldShowScrollToTopButton,
  };
}
