import type { EChartsType } from 'echarts/core';
import type { Ref } from 'vue';
import type VChart from 'vue-echarts';
import { assert, type BigNumber, type NetValue } from '@rotki/common';
import { type TooltipData, useGraphTooltip } from '@/composables/graphs';

interface UseNetValueEventHandlersParams {
  chartInstance: Ref<InstanceType<typeof VChart> | undefined>;
  chartContainer: Ref<HTMLElement | undefined>;
  chartData: Ref<NetValue>;
  onHover: (timestamp: number, value: BigNumber) => void;
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
  const isDragging = ref<boolean>(false);
  const dragStartPos = ref({ x: 0, y: 0 });

  let chartEventHandlers: (() => void)[] = [];

  const {
    chartContainer,
    chartData,
    chartInstance,
    onHover,
  } = params;

  const { resetTooltipData, tooltipData } = useGraphTooltip();

  function resetTooltip(): void {
    resetTooltipData();
    set(lastHover, undefined);
  }

  /**
     * Calculates the position for a tooltip based on the current mouse position while ensuring
     * the tooltip does not overflow the boundaries of a specified container.
     *
     * The method adjusts the tooltip position dynamically by flipping its placement
     * horizontally or vertically if it exceeds the container's dimensions.
     *
     * @return {Object} An object containing the x and y coordinates for the tooltip position:
     * - x: The adjusted horizontal position for the tooltip.
     * - y: The adjusted vertical position for the tooltip.
     */
  function calculateTooltipPosition(): { x: number; y: number } {
    // Start from the last known mouse coordinates
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
     * Sets up the handler for adjusting the axis pointer and tooltip display on the provided ECharts instance.
     *
     * @param {EChartsType} instance - The instance of the ECharts chart on which the axis pointer handler will be set up.
     * @return {void} This function does not return a value.
     */
  function setupAxisPointerHandler(instance: EChartsType): void {
    instance.on('updateAxisPointer', (event: any) => {
      const { axesInfo, dataIndex } = event;
      const xAxisInfo = axesInfo?.[0];

      const netValues = get(chartData).data;
      const netValue = netValues[dataIndex];
      const currentBalance = dataIndex === netValues.length - 1;

      if (!xAxisInfo || !netValue) {
        resetTooltip();
        return;
      }

      const timestamp = xAxisInfo.value;
      const tooltipPosition = calculateTooltipPosition();

      set(tooltipData, {
        currentBalance,
        timestamp,
        value: netValue,
        visible: true,
        ...tooltipPosition,
      });

      updateLastHover(currentBalance, timestamp, netValue);
    });
  }

  /**
     * Sets up an event handler to hide the tooltip when the pointer leaves the entire chart area.
     *
     * @param {EChartsType} instance - The ECharts instance to configure the mouse leave handler for.
     * @return {void} Does not return a value.
     */
  function setupMouseLeaveHandler(instance: EChartsType): void {
    instance.getZr().on('globalout', () => {
      resetTooltip();
    });
  }

  function setupMoveMoveHandler(instance: EChartsType): void {
    instance.getZr().on('mousemove', (event: MouseEvent) => {
      set(mousePos, {
        x: event.offsetX,
        y: event.offsetY,
      });
    });
  }

  /**
     * Sets up a handler for double-click events on the given ECharts instance.
     * The handler includes resetting the data zoom to its initial state.
     *
     * @param {EChartsType} instance - The ECharts instance on which the double-click handler is set up.
     * @return {void} This function does not return a value.
     */
  function setupDoubleClickHandler(instance: EChartsType): void {
    instance.getZr().on('dblclick', () => {
      if (isDefined(clickTimer)) {
        clearTimeout(get(clickTimer));
        set(clickTimer, undefined);
      }
      instance.dispatchAction({ end: 100, start: 0, type: 'dataZoom' });
    });
  }

  // Store event handlers for cleanup
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
 * Sets up a click event handler on the specified container element. This handler processes single and double-clicks
 * with a timer mechanism, allowing specific actions to be triggered based on the user's click interactions.
 *
 * @param {HTMLElement} container - The HTML element on which the click event listener will be added.
 * @return {void} This method does not return a value.
 */
  function setupContainerClickHandler(container: HTMLElement): void {
    // Track mouse down/up for drag detection
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

    containerEventHandlers.mouseup = (): void => {
      // Reset drag flag after a short delay to ensure click event sees the correct state
      setTimeout(() => {
        set(isDragging, false);
      }, 10);
    };

    containerEventHandlers.click = (): void => {
      // Ignore click if it was a drag operation
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

  function setupChartEventHandlers(): void {
    const currentChart = get(chartInstance);
    const container = get(chartContainer);

    if (!container || !currentChart?.chart) {
      return;
    }

    // Clear existing handlers
    chartEventHandlers.forEach(cleanup => cleanup());
    chartEventHandlers = [];

    const instance = currentChart.chart;
    setupAxisPointerHandler(instance);
    setupDoubleClickHandler(instance);
    setupMoveMoveHandler(instance);
    setupMouseLeaveHandler(instance);
    setupContainerClickHandler(container);
    setupZoomToolHandler();

    // Store cleanup functions
    chartEventHandlers = [
      (): EChartsType => instance?.off('updateAxisPointer'),
      (): EChartsType => instance?.off('finished'),
      (): void => instance?.getZr()?.off('dblclick'),
      (): void => instance?.getZr()?.off('mousemove'),
      (): void => instance?.getZr()?.off('globalout'),
      (): void => cleanupContainerEventHandlers(container),
    ];
  }

  // Cleanup on unmount
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
    tooltipData,
  };
}
