import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';

interface GraphBounds {
  width: number;
  height: number;
}

interface InteractionViewport {
  changeZoom: (amount: number) => void;
  dragging: Readonly<Ref<boolean>>;
  fitGraph: () => void;
  height: Readonly<Ref<number>>;
  modelZoom: Ref<number>;
  onClick: (event: MouseEvent) => void;
  onKeydown: (event: KeyboardEvent) => void;
  onPointerDown: (event: PointerEvent) => void;
  onPointerMove: (event: PointerEvent) => void;
  onPointerUp: () => void;
  onWheel: (event: WheelEvent) => void;
  transform: ComputedRef<string>;
  width: Readonly<Ref<number>>;
}

/** Keeps graph coordinates stable while the viewport pans and zooms. */
export function useInteractionViewport(bounds: MaybeRefOrGetter<GraphBounds>, viewport: Readonly<Ref<HTMLDivElement | null>>): InteractionViewport {
  const width = shallowRef<number>(600);
  const height = shallowRef<number>(600);
  const modelZoom = shallowRef<number>(1);
  const offset = shallowRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const dragging = shallowRef<boolean>(false);
  let pointer: { id: number; x: number; y: number; moved: boolean } | undefined;
  let suppressClick = false;
  const fitScale = computed<number>(() => Math.min(get(width) / toValue(bounds).width, get(height) / toValue(bounds).height, 1.5));
  const scale = computed<number>(() => get(fitScale) * get(modelZoom));
  const transform = computed<string>(() => `translate(${get(offset).x} ${get(offset).y}) scale(${get(scale)})`);

  function fitGraph(): void {
    set(modelZoom, 1);
    const size = toValue(bounds);
    set(offset, { x: (get(width) - size.width * get(fitScale)) / 2, y: (get(height) - size.height * get(fitScale)) / 2 });
  }

  function zoomAt(value: number, x: number, y: number): void {
    const next = Math.min(8, Math.max(0.25, value));
    const ratio = next / get(modelZoom);
    const previous = get(offset);
    set(offset, { x: x - (x - previous.x) * ratio, y: y - (y - previous.y) * ratio });
    set(modelZoom, next);
  }

  function changeZoom(amount: number): void {
    zoomAt(get(modelZoom) + amount, get(width) / 2, get(height) / 2);
  }

  function onWheel(event: WheelEvent): void {
    const rect = get(viewport)?.getBoundingClientRect();
    if (!rect)
      return;
    const units: Record<number, number> = { 0: 1, 1: 16, 2: get(height) };
    const delta = event.deltaY * (units[event.deltaMode] ?? 1);
    zoomAt(get(modelZoom) * Math.exp(-Math.max(-100, Math.min(100, delta)) * 0.002), event.clientX - rect.left, event.clientY - rect.top);
  }

  function onPointerDown(event: PointerEvent): void {
    if (event.button !== 0 || !event.isPrimary)
      return;
    suppressClick = false;
    pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, moved: false };
  }

  function onPointerMove(event: PointerEvent): void {
    if (pointer?.id !== event.pointerId)
      return;
    const dx = event.clientX - pointer.x;
    const dy = event.clientY - pointer.y;
    if (!pointer.moved && Math.hypot(dx, dy) < 4)
      return;
    get(viewport)?.setPointerCapture(event.pointerId);
    pointer = { id: pointer.id, x: event.clientX, y: event.clientY, moved: true };
    set(dragging, true);
    set(offset, { x: get(offset).x + dx, y: get(offset).y + dy });
  }

  function onPointerUp(): void {
    if (pointer)
      suppressClick = pointer.moved;
    pointer = undefined;
    set(dragging, false);
  }

  function onClick(event: MouseEvent): void {
    if (suppressClick) {
      event.stopPropagation();
      suppressClick = false;
    }
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.target !== get(viewport))
      return;
    const directions: Record<string, readonly [number, number]> = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] };
    const direction = directions[event.key];
    if (direction) {
      event.preventDefault();
      set(offset, { x: get(offset).x + direction[0], y: get(offset).y + direction[1] });
    }
  }
  useResizeObserver(viewport, ([entry]) => {
    if (entry && entry.contentRect.width > 0 && entry.contentRect.height > 0) {
      set(width, entry.contentRect.width);
      set(height, entry.contentRect.height);
      fitGraph();
    }
  });
  watch(() => toValue(bounds), fitGraph, { immediate: true });

  return { changeZoom, dragging: readonly(dragging), fitGraph, height: readonly(height), modelZoom, onClick, onKeydown, onPointerDown, onPointerMove, onPointerUp, onWheel, transform, width: readonly(width) };
}
