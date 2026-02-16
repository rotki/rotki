import { createTestingPinia } from '@pinia/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSidebarResize } from '@/composables/use-sidebar-resize';
import { useAreaVisibilityStore } from '@/store/session/visibility';

interface MockTarget {
  setPointerCapture: ReturnType<typeof vi.fn>;
  releasePointerCapture: ReturnType<typeof vi.fn>;
}

function createPointerEvent(overrides: Partial<PointerEvent> = {}): { event: PointerEvent; mockTarget: MockTarget } {
  const mockTarget: MockTarget = {
    setPointerCapture: vi.fn(),
    releasePointerCapture: vi.fn(),
  };
  const event = {
    preventDefault: vi.fn(),
    pointerId: 1,
    clientX: 0,
    target: mockTarget,
    ...overrides,
  };
  // Single unavoidable cast: we can't fully implement every PointerEvent property
  return { event: event as PointerEvent, mockTarget };
}

describe('composables::use-sidebar-resize', () => {
  let originalInnerWidth: number;

  beforeEach(() => {
    const pinia = createTestingPinia();
    setActivePinia(pinia);
    originalInnerWidth = window.innerWidth;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });

  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', { value: originalInnerWidth, writable: true, configurable: true });
  });

  it('should initialize with default width', () => {
    const { widthPx, dragging } = useSidebarResize();

    expect(get(widthPx)).toBe('516px');
    expect(get(dragging)).toBe(false);
  });

  it('should reflect store pinnedWidth', () => {
    const store = useAreaVisibilityStore();
    store.pinnedWidth = 600;

    const { widthPx } = useSidebarResize();

    expect(get(widthPx)).toBe('600px');
  });

  describe('onPointerDown', () => {
    it('should set dragging to true and apply body styles', () => {
      const { dragging, onPointerDown } = useSidebarResize();
      const { event, mockTarget } = createPointerEvent();

      onPointerDown(event);

      expect(get(dragging)).toBe(true);
      expect(mockTarget.setPointerCapture).toHaveBeenCalledWith(1);
      expect(document.body.style.cursor).toBe('col-resize');
      expect(document.body.style.userSelect).toBe('none');
    });
  });

  describe('onPointerMove', () => {
    it('should not update width when not dragging', () => {
      const store = useAreaVisibilityStore();
      store.pinnedWidth = 520;
      const { onPointerMove } = useSidebarResize();

      onPointerMove(createPointerEvent({ clientX: 500 }).event);

      expect(store.pinnedWidth).toBe(520);
    });

    it('should update width when dragging', () => {
      Object.defineProperty(window, 'innerWidth', { value: 1200, writable: true, configurable: true });
      const store = useAreaVisibilityStore();
      const { onPointerDown, onPointerMove } = useSidebarResize();

      onPointerDown(createPointerEvent().event);
      onPointerMove(createPointerEvent({ clientX: 500 }).event);

      // width = 1200 - 500 = 700, max = min(1000, 900) = 900, clamped = 700
      expect(store.pinnedWidth).toBe(700);
    });

    it('should clamp width to minimum 500', () => {
      Object.defineProperty(window, 'innerWidth', { value: 1200, writable: true, configurable: true });
      const store = useAreaVisibilityStore();
      const { onPointerDown, onPointerMove } = useSidebarResize();

      onPointerDown(createPointerEvent().event);
      onPointerMove(createPointerEvent({ clientX: 900 }).event);

      // width = 1200 - 900 = 300, clamped to min 516
      expect(store.pinnedWidth).toBe(516);
    });

    it('should clamp width to 75% of window when window is narrow', () => {
      Object.defineProperty(window, 'innerWidth', { value: 1200, writable: true, configurable: true });
      const store = useAreaVisibilityStore();
      const { onPointerDown, onPointerMove } = useSidebarResize();

      onPointerDown(createPointerEvent().event);
      onPointerMove(createPointerEvent({ clientX: 100 }).event);

      // width = 1200 - 100 = 1100, max = min(1000, 900) = 900, clamped to 900
      expect(store.pinnedWidth).toBe(900);
    });

    it('should cap at 1000 when window is very wide', () => {
      Object.defineProperty(window, 'innerWidth', { value: 2000, writable: true, configurable: true });
      const store = useAreaVisibilityStore();
      const { onPointerDown, onPointerMove } = useSidebarResize();

      onPointerDown(createPointerEvent().event);
      onPointerMove(createPointerEvent({ clientX: 500 }).event);

      // width = 2000 - 500 = 1500, max = min(1000, 1500) = 1000, clamped to 1000
      expect(store.pinnedWidth).toBe(1000);
    });
  });

  describe('onPointerUp', () => {
    it('should not do anything when not dragging', () => {
      const { dragging, onPointerUp } = useSidebarResize();
      const { event, mockTarget } = createPointerEvent();

      onPointerUp(event);

      expect(get(dragging)).toBe(false);
      expect(mockTarget.releasePointerCapture).not.toHaveBeenCalled();
    });

    it('should set dragging to false and clear body styles', () => {
      const { dragging, onPointerDown, onPointerUp } = useSidebarResize();
      const { event, mockTarget } = createPointerEvent();

      onPointerDown(event);
      expect(get(dragging)).toBe(true);

      onPointerUp(event);

      expect(get(dragging)).toBe(false);
      expect(mockTarget.releasePointerCapture).toHaveBeenCalledWith(1);
      expect(document.body.style.cursor).toBe('');
      expect(document.body.style.userSelect).toBe('');
    });
  });
});
