import { defaultDocument, useScroll } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef } from 'vue';

interface UseCoreScrollReturn {
  scrollToTop: () => void;
  shouldShowScrollToTopButton: ComputedRef<boolean>;
}

export function useCoreScroll(): UseCoreScrollReturn {
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
