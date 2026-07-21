import type { ComputedRef, Ref } from 'vue';
import { defaultDocument } from '@vueuse/core';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PINNED_DEFAULT_WIDTH, PINNED_MAX_VIEWPORT_RATIO, PINNED_MAX_WIDTH } from '@/modules/shell/layout/sidebar-resize-constants';

export function useSidebarResize(): {
  dragging: Ref<boolean>;
  widthPx: ComputedRef<string>;
  onPointerDown: (event: PointerEvent) => void;
  onPointerMove: (event: PointerEvent) => void;
  onPointerUp: (event: PointerEvent) => void;
} {
  const { pinnedDragging: dragging, pinnedWidth } = storeToRefs(useAreaVisibilityStore());
  const { isLgAndDown } = useBreakpoint();
  const { width: windowWidth } = useWindowSize();
  let rafId = 0;

  const widthPx = computed<string>(() => {
    if (get(isLgAndDown))
      return `${PINNED_DEFAULT_WIDTH}px`;
    return `${get(pinnedWidth)}px`;
  });

  function clampWidth(width: number): number {
    const max = Math.min(PINNED_MAX_WIDTH, get(windowWidth) * PINNED_MAX_VIEWPORT_RATIO);
    return Math.max(PINNED_DEFAULT_WIDTH, Math.min(width, max));
  }

  function onPointerDown(event: PointerEvent): void {
    event.preventDefault();
    set(dragging, true);
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
    const body = defaultDocument?.body;
    if (body) {
      body.style.cursor = 'col-resize';
      body.style.userSelect = 'none';
    }
  }

  function onPointerMove(event: PointerEvent): void {
    if (!get(dragging))
      return;

    if (rafId)
      cancelAnimationFrame(rafId);

    rafId = requestAnimationFrame(() => {
      const newWidth = clampWidth(get(windowWidth) - event.clientX);
      set(pinnedWidth, newWidth);
      rafId = 0;
    });
  }

  function onPointerUp(event: PointerEvent): void {
    if (!get(dragging))
      return;

    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }

    set(dragging, false);
    (event.target as HTMLElement).releasePointerCapture(event.pointerId);
    const body = defaultDocument?.body;
    if (body) {
      body.style.cursor = '';
      body.style.userSelect = '';
    }
  }

  return {
    dragging,
    widthPx,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  };
}
