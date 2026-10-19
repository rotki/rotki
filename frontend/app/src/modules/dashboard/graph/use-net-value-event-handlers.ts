import type { EChartsType } from 'echarts/core';
import type { MaybeRefOrGetter, Ref, ShallowRef } from 'vue';
import type VChart from 'vue-echarts';
import type { NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { assert, type BigNumber } from '@rotki/common';
import { readZoomFields, resolveZoomRange } from '@/modules/dashboard/graph/net-value-zoom-event';
import { type TooltipData, useGraphTooltip } from '@/modules/statistics/use-graph-tooltip';

const DRAG_FLAG_CLEAR_DELAY_MS = 10;

interface UseNetValueEventHandlersParams {
  chartInstance: Readonly<ShallowRef<InstanceType<typeof VChart> | null>>;
  chartContainer: Readonly<ShallowRef<HTMLElement | null>>;
  chartData: MaybeRefOrGetter<NetValueChartData>;
  onHover: (timestamp: number, value: BigNumber) => void;
  onZoomChange?: (range: NetValueZoomRange | undefined) => void;
}

interface UseNetValueEventHandlersReturn {
  setupChartEventHandlers: () => void;
  setupZoomToolHandler: () => void;
  tooltipData: Ref<TooltipData>;
}

export function useNetValueEventHandlers(params: UseNetValueEventHandlersParams): UseNetValueEventHandlersReturn {
  const lastHover = ref<{ timestamp: number; value: BigNumber }>();
  const mousePos = ref({ x: 0, y: 0 });
  const clickTimer = ref<ReturnType<typeof setTimeout>>();
  const isDragging = shallowRef<boolean>(false);
  const dragStartPos = ref({ x: 0, y: 0 });

  let chartEventHandlers: (() => void)[] = [];

  const {
    chartContainer,
    chartData,
    chartInstance,
    onHover,
    onZoomChange,
  } = params;

  const { modelTooltipData, resetTooltipData } = useGraphTooltip();

  function resetTooltip(): void {
    resetTooltipData();
    set(lastHover, undefined);
  }

  /**
   * Places the tooltip near the pointer without letting it overflow its container.
   *
   * @remarks
   * Flips the placement horizontally or vertically when the tooltip would cross an edge.
   *
   * @returns the tooltip's adjusted `x` and `y`, in container coordinates
   */
  function calculateTooltipPosition(): { x: number; y: number } {
    const pos = get(mousePos);
    let cursorX = pos.x + 20;
    let cursorY = pos.y + 20;

    // Estimate tooltip size for boundary flipping
    const tooltipWidth = 150;
    const tooltipHeight = 60;

    const container = get(chartContainer);
    assert(container, 'Chart container not found');
    const containerRect = container.getBoundingClientRect();
    if (containerRect) {
      // If overflowing to the right => flip to the left
      if (cursorX + tooltipWidth > containerRect.width) {
        cursorX = pos.x - 20 - tooltipWidth;
      }
      // If overflowing bottom => flip up
      if (cursorY + tooltipHeight > containerRect.height) {
        cursorY = pos.y - 20 - tooltipHeight;
      }
    }
    return { x: cursorX, y: cursorY };
  }

  function updateLastHover(currentBalance: boolean, timestamp: number, netValue: BigNumber): void {
    set(lastHover, currentBalance
      ? undefined
      : {
          timestamp,
          value: netValue,
        });
  }

  /**
   * Sets up the handler that moves the axis pointer and the tooltip together.
   */
  function setupAxisPointerHandler(instance: EChartsType): () => void {
    const handler = (event: any): void => {
      const { axesInfo, dataIndex } = event;
      const xAxisInfo = axesInfo?.[0];

      const { data: netValues, snapshotCount } = toValue(chartData);
      const netValue = netValues[dataIndex];
      const currentBalance = dataIndex === netValues.length - 1;
      const isSnapshot = dataIndex < snapshotCount;

      if (!xAxisInfo || !netValue) {
        resetTooltip();
        return;
      }

      const timestamp = xAxisInfo.value;
      const tooltipPosition = calculateTooltipPosition();

      set(modelTooltipData, {
        currentBalance,
        timestamp,
        value: netValue,
        visible: true,
        ...tooltipPosition,
      });

      updateLastHover(!isSnapshot, timestamp, netValue);
    };
    instance.on('updateAxisPointer', handler);
    return (): void => {
      instance.off('updateAxisPointer', handler);
    };
  }

  /**
   * Hides the tooltip when the pointer leaves the chart area entirely.
   */
  function setupMouseLeaveHandler(instance: EChartsType): () => void {
    const handler = (): void => resetTooltip();
    instance.getZr().on('globalout', handler);
    return (): void => instance.getZr()?.off('globalout', handler);
  }

  function setupMouseMoveHandler(instance: EChartsType): () => void {
    const handler = (event: MouseEvent): void => {
      set(mousePos, {
        x: event.offsetX,
        y: event.offsetY,
      });
    };
    instance.getZr().on('mousemove', handler);
    return (): void => instance.getZr()?.off('mousemove', handler);
  }

  /**
   * Handles double-click on the chart, which resets the data zoom to its initial state.
   */
  function setupDoubleClickHandler(instance: EChartsType): () => void {
    const handler = (): void => {
      if (isDefined(clickTimer)) {
        clearTimeout(get(clickTimer));
        set(clickTimer, undefined);
      }
      instance.dispatchAction({ end: 100, start: 0, type: 'dataZoom' });
    };
    instance.getZr().on('dblclick', handler);
    return (): void => instance.getZr()?.off('dblclick', handler);
  }

  let containerEventHandlers: {
    mousedown?: (e: MouseEvent) => void;
    mousemove?: (e: MouseEvent) => void;
    mouseup?: () => void;
    click?: (event: MouseEvent) => void;
  } = {};

  /**
   * Removes all container event listeners and clears the handlers
   */
  function cleanupContainerEventHandlers(container?: HTMLElement): void {
    const eventTypes = ['click', 'mousedown', 'mousemove', 'mouseup'] as const;

    eventTypes.forEach((eventType) => {
      const handler = containerEventHandlers[eventType];
      if (handler) {
        container?.removeEventListener(eventType, handler);
      }
    });

    containerEventHandlers = {};
  }

  /**
   * Clears the drag flag once the click that follows this mouseup has been dispatched.
   *
   * @remarks
   * The browser fires `click` after `mouseup`, so clearing the flag synchronously would let the
   * click that merely ended a drag read it as false and act as an ordinary click. The delay only
   * has to outlast that dispatch.
   */
  function clearDragAfterClickIsDispatched(): void {
    setTimeout(() => {
      set(isDragging, false);
    }, DRAG_FLAG_CLEAR_DELAY_MS);
  }

  /**
   * Handles clicks on the container, separating a single click from a double one.
   *
   * @remarks
   * A timer holds the single-click action back long enough for a second click to cancel it, and
   * mousedown/mouseup positions are tracked so a drag is not mistaken for a click.
   */
  function setupContainerClickHandler(container: HTMLElement): void {
    containerEventHandlers.mousedown = (e): void => {
      set(dragStartPos, { x: e.offsetX, y: e.offsetY });
      set(isDragging, false);
    };

    containerEventHandlers.mousemove = (e): void => {
      if (e.buttons === 1) { // Left mouse button is pressed
        const startPos = get(dragStartPos);
        const distance = Math.hypot(
          e.offsetX - startPos.x,
          e.offsetY - startPos.y,
        );
        // Consider it a drag if moved more than 5 pixels
        if (distance > 5) {
          set(isDragging, true);
        }
      }
    };

    containerEventHandlers.mouseup = clearDragAfterClickIsDispatched;

    containerEventHandlers.click = (): void => {
      if (get(isDragging)) {
        return;
      }

      if (isDefined(clickTimer)) {
        clearTimeout(get(clickTimer));
        set(clickTimer, undefined);
      }
      else {
        set(clickTimer, setTimeout(() => {
          set(clickTimer, undefined);
          const hover = get(lastHover);
          if (hover) {
            onHover(hover.timestamp / 1000, hover.value);
          }
        }, 200));
      }
    };

    container.addEventListener('click', containerEventHandlers.click);
    container.addEventListener('mousedown', containerEventHandlers.mousedown);
    container.addEventListener('mousemove', containerEventHandlers.mousemove);
    container.addEventListener('mouseup', containerEventHandlers.mouseup);
  }

  function setupZoomChangeHandler(instance: EChartsType): () => void {
    if (!onZoomChange)
      return (): void => {};

    const handler = (...args: unknown[]): void => {
      const { times } = toValue(chartData);
      const last = times.at(-1);
      if (times.length === 0 || last === undefined) {
        onZoomChange(undefined);
        return;
      }

      const range = resolveZoomRange(readZoomFields(args[0]), times);
      if (range === undefined) {
        onZoomChange(undefined);
        return;
      }

      // Full-range selection collapses to undefined so consumers stay on the unzoomed path.
      if (range.start <= times[0] && range.end >= last) {
        onZoomChange(undefined);
        return;
      }
      onZoomChange(range);
    };

    instance.on('datazoom', handler);
    return (): void => {
      instance.off('datazoom', handler);
    };
  }

  function setupZoomToolHandler(): void {
    const instance = get(chartInstance)?.chart;
    if (!instance) {
      return;
    }

    const activateZoomTool = (): void => {
      instance.dispatchAction({
        dataZoomSelectActive: true,
        key: 'dataZoomSelect',
        type: 'takeGlobalCursor',
      });

      instance.off('finished', activateZoomTool);
    };
    setTimeout(activateZoomTool, 300);
    instance.on('finished', activateZoomTool);
  }

  /**
   * Registers the chart and container handlers, replacing any from an earlier run.
   *
   * @remarks
   * Each cleanup removes only the handler it added. An `off` without one also removes the
   * listeners ECharts registers for itself, so once a theme change re-ran this setup the slider
   * no longer dragged and the tooltip no longer showed.
   */
  function setupChartEventHandlers(): void {
    const currentChart = get(chartInstance);
    const container = get(chartContainer);

    if (!container || !currentChart?.chart) {
      return;
    }

    chartEventHandlers.forEach(cleanup => cleanup());
    chartEventHandlers = [];

    const instance = currentChart.chart;
    setupContainerClickHandler(container);
    setupZoomToolHandler();

    chartEventHandlers = [
      setupAxisPointerHandler(instance),
      setupDoubleClickHandler(instance),
      setupMouseMoveHandler(instance),
      setupMouseLeaveHandler(instance),
      setupZoomChangeHandler(instance),
      (): void => cleanupContainerEventHandlers(container),
    ];
  }

  onUnmounted(() => {
    chartEventHandlers.forEach(cleanup => cleanup());
    const timer = get(clickTimer);
    if (timer) {
      clearTimeout(timer);
      set(clickTimer, undefined);
    }
  });

  return {
    setupChartEventHandlers,
    setupZoomToolHandler,
    tooltipData: modelTooltipData,
  };
}
