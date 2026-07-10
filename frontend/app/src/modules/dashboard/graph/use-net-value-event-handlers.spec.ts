import type VChart from 'vue-echarts';
import type { NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref, type Ref, type ShallowRef, shallowRef, type VNode } from 'vue';
import {
  readZoomFields,
  resolveZoomRange,
  useNetValueEventHandlers,
} from '@/modules/dashboard/graph/use-net-value-event-handlers';

describe('readZoomFields', () => {
  it('should read top-level fields when batch is absent (slider drag shape)', () => {
    expect(readZoomFields({ end: 80, endValue: 2000, start: 20, startValue: 1000 })).toEqual({
      end: 80,
      endValue: 2000,
      start: 20,
      startValue: 1000,
    });
  });

  it('should read batch[0] when present (inside-zoom shape)', () => {
    expect(readZoomFields({
      batch: [{ end: 90, endValue: 3000, start: 10, startValue: 500 }],
    })).toEqual({ end: 90, endValue: 3000, start: 10, startValue: 500 });
  });

  it('should accept percent-only batch entries (slider without axis values)', () => {
    expect(readZoomFields({ batch: [{ end: 75, start: 25 }] })).toEqual({
      end: 75,
      endValue: undefined,
      start: 25,
      startValue: undefined,
    });
  });

  it('should return undefined for non-object input', () => {
    expect(readZoomFields(undefined)).toBeUndefined();
    expect(readZoomFields(null)).toBeUndefined();
    expect(readZoomFields('event')).toBeUndefined();
  });

  it('should return undefined when batch is empty and no top-level fields are set', () => {
    expect(readZoomFields({ batch: [null] })).toBeUndefined();
    // empty batch falls through to the top-level read, which yields all-undefined fields
    expect(resolveZoomRange(readZoomFields({ batch: [] }), [1, 2])).toBeUndefined();
  });
});

describe('resolveZoomRange', () => {
  const times = [1000, 2000, 3000, 4000, 5000];

  it('should convert ms axis values to second-based range', () => {
    expect(resolveZoomRange({ endValue: 4000000, startValue: 2000000 }, times)).toEqual({
      end: 4000,
      start: 2000,
    });
  });

  it('should map percentage range against the times window when axis values are absent', () => {
    // 25%..75% of [1000, 5000] -> [2000, 4000]
    expect(resolveZoomRange({ end: 75, start: 25 }, times)).toEqual({ end: 4000, start: 2000 });
  });

  it('should prefer axis values when both shapes are present', () => {
    expect(resolveZoomRange({ end: 100, endValue: 3000000, start: 0, startValue: 1500000 }, times)).toEqual({
      end: 3000,
      start: 1500,
    });
  });

  it('should return undefined when only one bound is provided', () => {
    expect(resolveZoomRange({ start: 25 }, times)).toBeUndefined();
    expect(resolveZoomRange({ startValue: 1000 }, times)).toBeUndefined();
  });

  it('should return undefined when fields are missing or times empty', () => {
    expect(resolveZoomRange(undefined, times)).toBeUndefined();
    expect(resolveZoomRange({ end: 75, start: 25 }, [])).toBeUndefined();
  });
});

type EventHandler = (arg: any) => void;

interface FakeChart {
  chart: {
    on: ReturnType<typeof vi.fn>;
    off: ReturnType<typeof vi.fn>;
    getZr: ReturnType<typeof vi.fn>;
    dispatchAction: ReturnType<typeof vi.fn>;
  };
  handlers: Map<string, EventHandler>;
  zr: { on: ReturnType<typeof vi.fn>; off: ReturnType<typeof vi.fn> };
  zrHandlers: Map<string, EventHandler>;
}

function createFakeChart(): FakeChart {
  const handlers = new Map<string, EventHandler>();
  const zrHandlers = new Map<string, EventHandler>();
  const zr = {
    off: vi.fn((event: string) => { zrHandlers.delete(event); }),
    on: vi.fn((event: string, handler: EventHandler) => { zrHandlers.set(event, handler); }),
  };
  const chart = {
    dispatchAction: vi.fn(),
    getZr: vi.fn(() => zr),
    off: vi.fn((event: string) => {
      handlers.delete(event);
      return chart;
    }),
    on: vi.fn((event: string, handler: EventHandler) => { handlers.set(event, handler); }),
  };
  return { chart, handlers, zr, zrHandlers };
}

// The fake chart intentionally implements only the members the composable
// touches (it reads `.chart` and its echarts methods), so a single contained
// assertion bridges it to the vue-echarts instance type.
function chartInstanceRef(chart: FakeChart['chart'] | null): ShallowRef<InstanceType<typeof VChart> | null> {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the fake only mocks the members the SUT uses; contained here
  const instance = chart === null ? null : ({ chart } as unknown as InstanceType<typeof VChart>);
  return shallowRef(instance);
}

describe('useNetValueEventHandlers', () => {
  let fake: FakeChart;
  let container: HTMLElement;
  let containerHandlers: Map<string, EventHandler>;
  let removeSpy: ReturnType<typeof vi.spyOn>;
  let onHover: (timestamp: number, value: BigNumber) => void;
  let onZoomChange: (range: NetValueZoomRange | undefined) => void;
  let chartData: Ref<NetValueChartData>;

  function setupHarness(withZoom = true): {
    setupChartEventHandlers: () => void;
    setupZoomToolHandler: () => void;
    tooltipData: ReturnType<typeof useNetValueEventHandlers>['tooltipData'];
    unmount: () => void;
  } {
    let api: ReturnType<typeof useNetValueEventHandlers>;
    const wrapper = mount(defineComponent({
      setup(): () => VNode {
        api = useNetValueEventHandlers({
          chartContainer: ref(container),
          chartData,
          chartInstance: chartInstanceRef(fake.chart),
          onHover,
          onZoomChange: withZoom ? onZoomChange : undefined,
        });
        return () => h('div');
      },
    }));
    return { ...api!, unmount: () => wrapper.unmount() };
  }

  beforeEach(() => {
    vi.useFakeTimers();
    fake = createFakeChart();
    container = document.createElement('div');
    container.getBoundingClientRect = (): DOMRect => new DOMRect(0, 0, 500, 300);
    containerHandlers = new Map();
    vi.spyOn(container, 'addEventListener').mockImplementation((event: string, handler: EventListenerOrEventListenerObject): void => {
      if (typeof handler === 'function')
        containerHandlers.set(event, handler);
    });
    removeSpy = vi.spyOn(container, 'removeEventListener').mockImplementation((event: string): void => {
      containerHandlers.delete(event);
    });
    onHover = vi.fn();
    onZoomChange = vi.fn();
    chartData = ref<NetValueChartData>({
      data: [bigNumberify(10), bigNumberify(20), bigNumberify(30)],
      snapshotCount: 2,
      times: [1000, 2000, 3000],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('should not register handlers when the chart instance is missing', () => {
    const harness = mount(defineComponent({
      setup(): () => VNode {
        useNetValueEventHandlers({
          chartContainer: ref(container),
          chartData,
          chartInstance: chartInstanceRef(null),
          onHover,
        }).setupChartEventHandlers();
        return () => h('div');
      },
    }));
    expect(fake.chart.on).not.toHaveBeenCalled();
    expect(containerHandlers.size).toBe(0);
    harness.unmount();
  });

  it('should register chart, zrender and container handlers on setup', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();

    expect(fake.chart.on).toHaveBeenCalledWith('updateAxisPointer', expect.any(Function));
    expect(fake.chart.on).toHaveBeenCalledWith('datazoom', expect.any(Function));
    expect([...fake.zrHandlers.keys()]).toEqual(expect.arrayContaining(['dblclick', 'mousemove', 'globalout']));
    expect([...containerHandlers.keys()]).toEqual(expect.arrayContaining(['click', 'mousedown', 'mousemove', 'mouseup']));
    unmount();
  });

  it('should not register the datazoom handler when no onZoomChange is provided', () => {
    const { setupChartEventHandlers, unmount } = setupHarness(false);
    setupChartEventHandlers();
    expect(fake.handlers.has('datazoom')).toBe(false);
    unmount();
  });

  it('should populate tooltip data on axis pointer over a snapshot point', () => {
    const { setupChartEventHandlers, tooltipData, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.zrHandlers.get('mousemove')?.({ offsetX: 40, offsetY: 50 });

    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 1 });

    expect(get(tooltipData)).toMatchObject({
      currentBalance: false,
      timestamp: 2000,
      visible: true,
      x: 60,
      y: 70,
    });
    unmount();
  });

  it('should flag currentBalance for the last data point', () => {
    const { setupChartEventHandlers, tooltipData, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 3000 }], dataIndex: 2 });
    expect(get(tooltipData).currentBalance).toBe(true);
    unmount();
  });

  it('should flip the tooltip position near the container edges', () => {
    const { setupChartEventHandlers, tooltipData, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.zrHandlers.get('mousemove')?.({ offsetX: 480, offsetY: 290 });
    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 1 });

    // 480 + 20 + 150 > 500 -> flip left: 480 - 20 - 150 = 310; 290 + 20 + 60 > 300 -> flip up: 290 - 20 - 60 = 210
    expect(get(tooltipData)).toMatchObject({ x: 310, y: 210 });
    unmount();
  });

  it('should hide the tooltip when axis info or data point is missing', () => {
    const { setupChartEventHandlers, tooltipData, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 1 });
    expect(get(tooltipData).visible).toBe(true);

    fake.handlers.get('updateAxisPointer')?.({ axesInfo: undefined, dataIndex: 1 });
    expect(get(tooltipData).visible).toBe(false);

    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 99 });
    expect(get(tooltipData).visible).toBe(false);
    unmount();
  });

  it('should reset the tooltip when the pointer leaves the chart', () => {
    const { setupChartEventHandlers, tooltipData, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 1 });
    expect(get(tooltipData).visible).toBe(true);

    fake.zrHandlers.get('globalout')?.(undefined);
    expect(get(tooltipData).visible).toBe(false);
    unmount();
  });

  it('should reset the zoom on double click and clear a pending single-click timer', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();

    // first click arms the single-click timer
    containerHandlers.get('click')?.({});
    fake.zrHandlers.get('dblclick')?.(undefined);

    expect(fake.chart.dispatchAction).toHaveBeenCalledWith({ end: 100, start: 0, type: 'dataZoom' });
    // timer was cleared, so advancing does not fire onHover
    vi.advanceTimersByTime(500);
    expect(onHover).not.toHaveBeenCalled();
    unmount();
  });

  it('should emit a hover on a single click after a snapshot pointer move', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    // snapshot point records lastHover
    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 1 });

    containerHandlers.get('mousedown')?.({ offsetX: 0, offsetY: 0 });
    containerHandlers.get('click')?.({});
    vi.advanceTimersByTime(200);

    expect(onHover).toHaveBeenCalledWith(2, bigNumberify(20));
    unmount();
  });

  it('should ignore a click that follows a drag', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 1 });

    containerHandlers.get('mousedown')?.({ offsetX: 0, offsetY: 0 });
    containerHandlers.get('mousemove')?.({ buttons: 1, offsetX: 40, offsetY: 0 });
    containerHandlers.get('click')?.({});
    vi.advanceTimersByTime(200);

    expect(onHover).not.toHaveBeenCalled();
    unmount();
  });

  it('should treat a second quick click as a double click and cancel the hover', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('updateAxisPointer')?.({ axesInfo: [{ value: 2000 }], dataIndex: 1 });

    containerHandlers.get('click')?.({});
    containerHandlers.get('click')?.({});
    vi.advanceTimersByTime(300);

    expect(onHover).not.toHaveBeenCalled();
    unmount();
  });

  it('should activate the zoom select tool after the chart finishes rendering', () => {
    const { setupZoomToolHandler, unmount } = setupHarness();
    setupZoomToolHandler();

    expect(fake.chart.on).toHaveBeenCalledWith('finished', expect.any(Function));
    vi.advanceTimersByTime(300);
    expect(fake.chart.dispatchAction).toHaveBeenCalledWith({
      dataZoomSelectActive: true,
      key: 'dataZoomSelect',
      type: 'takeGlobalCursor',
    });
    expect(fake.chart.off).toHaveBeenCalledWith('finished', expect.any(Function));
    unmount();
  });

  it('should emit the resolved range on a partial datazoom selection', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('datazoom')?.({ endValue: 2000000, startValue: 1500000 });
    expect(onZoomChange).toHaveBeenCalledWith({ end: 2000, start: 1500 });
    unmount();
  });

  it('should collapse a full-range datazoom selection to undefined', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('datazoom')?.({ end: 100, start: 0 });
    expect(onZoomChange).toHaveBeenCalledWith(undefined);
    unmount();
  });

  it('should emit undefined when the times series is empty', () => {
    set(chartData, { data: [], snapshotCount: 0, times: [] });
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('datazoom')?.({ endValue: 2000000, startValue: 1500000 });
    expect(onZoomChange).toHaveBeenCalledWith(undefined);
    unmount();
  });

  it('should emit undefined when the zoom event carries no usable fields', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.handlers.get('datazoom')?.({});
    expect(onZoomChange).toHaveBeenCalledWith(undefined);
    unmount();
  });

  it('should tear down every handler when the setup runs again', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    fake.chart.off.mockClear();
    fake.zr.off.mockClear();

    setupChartEventHandlers();

    expect(fake.chart.off).toHaveBeenCalledWith('updateAxisPointer');
    expect(fake.chart.off).toHaveBeenCalledWith('datazoom');
    expect(fake.zr.off).toHaveBeenCalledWith('dblclick');
    unmount();
  });

  it('should clean up handlers and pending timers on unmount', () => {
    const { setupChartEventHandlers, unmount } = setupHarness();
    setupChartEventHandlers();
    // arm a single-click timer so unmount clears it
    containerHandlers.get('click')?.({});

    unmount();

    expect(fake.chart.off).toHaveBeenCalledWith('updateAxisPointer');
    expect(fake.zr.off).toHaveBeenCalledWith('globalout');
    expect(removeSpy).toHaveBeenCalledWith('click', expect.any(Function));
    vi.advanceTimersByTime(500);
    expect(onHover).not.toHaveBeenCalled();
  });
});
