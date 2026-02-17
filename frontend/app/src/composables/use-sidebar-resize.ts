import type { ComputedRef, Ref } from 'vue';
import { PINNED_DEFAULT_WIDTH, PINNED_MAX_VIEWPORT_RATIO, PINNED_MAX_WIDTH } from '@/composables/use-sidebar-resize-constants';
import { useAreaVisibilityStore } from '@/store/session/visibility';

export function useSidebarResize(): {
  dragging: Ref<boolean>;
  widthPx: ComputedRef<string>;
  onPointerDown: (event: PointerEvent) => void;
  onPointerMove: (event: PointerEvent) => void;
  onPointerUp: (event: PointerEvent) => void;
} {
  const { pinnedWidth } = storeToRefs(useAreaVisibilityStore());
  const { isLgAndDown } = useBreakpoint();

  const dragging = ref<boolean>(false);

  const widthPx = computed<string>(() => {
    if (get(isLgAndDown))
      return `${PINNED_DEFAULT_WIDTH}px`;
    return `${get(pinnedWidth)}px`;
  });

  function clampWidth(width: number): number {
    const max = Math.min(PINNED_MAX_WIDTH, window.innerWidth * PINNED_MAX_VIEWPORT_RATIO);
    return Math.max(PINNED_DEFAULT_WIDTH, Math.min(width, max));
  }

  function onPointerDown(event: PointerEvent): void {
    event.preventDefault();
    set(dragging, true);
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function onPointerMove(event: PointerEvent): void {
    if (!get(dragging))
      return;

    const newWidth = clampWidth(window.innerWidth - event.clientX);
    set(pinnedWidth, newWidth);
  }

  function onPointerUp(event: PointerEvent): void {
    if (!get(dragging))
      return;

    set(dragging, false);
    (event.target as HTMLElement).releasePointerCapture(event.pointerId);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  return {
    dragging,
    widthPx,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  };
}
