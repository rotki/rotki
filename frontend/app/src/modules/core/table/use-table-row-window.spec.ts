import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type Ref, useTemplateRef, type VNode } from 'vue';
import {
  provideTableScroller,
  rangeSelection,
  rowOffset,
  rowRange,
  type RowWindowLayout,
  useTableRowWindow,
  useWindowedSelectAll,
  widenToggleAll,
} from '@/modules/core/table/use-table-row-window';

const flat: RowWindowLayout = { expandedHeight: 0, expandedIndex: -1, rowHeight: 40 };

describe('modules/core/table/use-table-row-window', () => {
  describe('rowOffset', () => {
    it('should place rows at whole row heights', () => {
      expect(rowOffset(flat, 5)).toBe(200);
    });

    it('should push only the rows below the expanded one down by its details', () => {
      const layout: RowWindowLayout = { expandedHeight: 100, expandedIndex: 2, rowHeight: 40 };

      expect(rowOffset(layout, 2)).toBe(80);
      expect(rowOffset(layout, 3)).toBe(220);
    });
  });

  describe('rowRange', () => {
    it('should cover the visible rows plus the overscan on each side', () => {
      expect(rowRange(flat, 100, 2000, 2400, 8)).toStrictEqual({ end: 69, start: 42 });
    });

    it('should stop at the first and the last row', () => {
      expect(rowRange(flat, 100, 0, 400, 8)).toStrictEqual({ end: 19, start: 0 });
      expect(rowRange(flat, 100, 3800, 4200, 8)).toStrictEqual({ end: 100, start: 87 });
    });

    it('should keep one row for a body scrolled fully out of view, so the table never reads as empty', () => {
      expect(rowRange(flat, 100, -900, -500, 0)).toStrictEqual({ end: 1, start: 0 });
      expect(rowRange(flat, 100, 9000, 9400, 0)).toStrictEqual({ end: 100, start: 99 });
    });

    it('should count the expanded row\'s details when finding the rows in view', () => {
      const layout: RowWindowLayout = { expandedHeight: 400, expandedIndex: 0, rowHeight: 40 };

      expect(rowRange(layout, 100, 840, 880, 0)).toStrictEqual({ end: 13, start: 11 });
    });

    it('should render nothing for a table with no rows', () => {
      expect(rowRange(flat, 0, 0, 400, 8)).toStrictEqual({ end: 0, start: 0 });
    });
  });

  describe('widenToggleAll', () => {
    it('should select every row of the table once the checkbox selected the rendered ones', () => {
      expect(widenToggleAll(['OTHER'], ['OTHER', 'A', 'B'], ['A', 'B', 'C', 'D']))
        .toStrictEqual(['OTHER', 'A', 'B', 'C', 'D']);
    });

    it('should clear every row of the table but keep rows of other tables', () => {
      expect(widenToggleAll(['OTHER', 'A', 'B', 'C'], ['OTHER', 'C'], ['A', 'B', 'C', 'D']))
        .toStrictEqual(['OTHER']);
    });
  });

  describe('useTableRowWindow', () => {
    const ROW_HEIGHT = 40;
    const rows = Array.from({ length: 100 }, (_, index) => `ASSET${index}`);

    let bodyTop = 0;
    let frames: FrameRequestCallback[] = [];

    function flushFrames(): void {
      const pending = frames;
      frames = [];
      pending.forEach(frame => frame(0));
    }

    /** Runs measurements and the renders they cause until neither asks for another. */
    async function settle(): Promise<void> {
      await nextTick();
      while (frames.length > 0) {
        flushFrames();
        await nextTick();
      }
    }

    beforeEach(() => {
      bodyTop = 0;
      frames = [];
      vi.stubGlobal('requestAnimationFrame', (frame: FrameRequestCallback) => frames.push(frame));
      vi.stubGlobal('cancelAnimationFrame', vi.fn());
      vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockImplementation(function (this: HTMLElement) {
        return this.dataset.id === 'row' ? ROW_HEIGHT : 0;
      });
      vi.spyOn(HTMLTableSectionElement.prototype, 'getBoundingClientRect').mockImplementation(() => new DOMRect(0, bodyTop, 800, 0));
    });

    afterEach(() => {
      vi.unstubAllGlobals();
      vi.restoreAllMocks();
    });

    interface WindowState {
      visibleRows: string[];
      paddingTop: number;
      paddingBottom: number;
      windowed: boolean;
    }

    function mountWindow(withScroller: boolean): { wrapper: VueWrapper; scroller: HTMLElement; state: Ref<WindowState | undefined> } {
      const scroller = document.createElement('div');
      vi.spyOn(scroller, 'getBoundingClientRect').mockImplementation(() => new DOMRect(0, 0, 800, 400));
      const state = ref<WindowState>();

      const Table = defineComponent({
        setup(): () => VNode {
          const result = useTableRowWindow(rows, { expandedIndex: -1, table: useTemplateRef('table') });
          watchEffect(() => {
            set(state, {
              paddingBottom: get(result.paddingBottom),
              paddingTop: get(result.paddingTop),
              visibleRows: get(result.visibleRows),
              windowed: result.windowed,
            });
          });
          return () => h('div', { ref: 'table' }, [
            h('table', [h('tbody', get(result.visibleRows).map(row => h('tr', { 'data-id': 'row', 'key': row })))]),
          ]);
        },
      });

      const Host = defineComponent({
        setup(): () => VNode {
          if (withScroller)
            provideTableScroller(shallowRef<HTMLElement>(scroller));
          return () => h(Table);
        },
      });

      return { scroller, state, wrapper: mount(Host) };
    }

    it('should render every row without a provided scroller', () => {
      const { state } = mountWindow(false);

      expect(get(state)).toStrictEqual({ paddingBottom: 0, paddingTop: 0, visibleRows: rows, windowed: false });
    });

    it('should render only the rows in view, standing in for the others with paddings', async () => {
      const { state } = mountWindow(true);
      await settle();

      expect(get(state)?.visibleRows).toStrictEqual(rows.slice(0, 19));
      expect(get(state)?.paddingTop).toBe(0);
      expect(get(state)?.paddingBottom).toBe(81 * ROW_HEIGHT);
    });

    it('should move the rendered rows along as the scroller scrolls', async () => {
      const { scroller, state } = mountWindow(true);
      await settle();

      bodyTop = -2000;
      scroller.dispatchEvent(new Event('scroll'));
      await settle();

      expect(get(state)?.visibleRows).toStrictEqual(rows.slice(42, 69));
      expect(get(state)?.paddingTop).toBe(42 * ROW_HEIGHT);
      expect(get(state)?.paddingBottom).toBe(31 * ROW_HEIGHT);
    });
  });

  describe('useWindowedSelectAll', () => {
    function clickOn(selector: string, root: HTMLElement, shiftKey: boolean = false): MouseEvent {
      const target = root.querySelector(selector);
      const event = new MouseEvent('click', { bubbles: true, cancelable: true, shiftKey });
      Object.defineProperty(event, 'target', { value: target });
      return event;
    }

    const root = document.createElement('table');
    root.innerHTML = '<thead><tr><th><label><input type="checkbox"></label></th></tr></thead>'
      + '<tbody><tr data-id="row"><td><label><input type="checkbox"></label></td></tr></tbody>';

    /** A body showing rows 20 to 22 of a longer list, with row 21 expanded. */
    const windowRoot = document.createElement('table');
    windowRoot.innerHTML = '<tbody>'
      + '<tr data-id="row"><td class="first"><input type="checkbox"></td><td class="name">20</td></tr>'
      + '<tr data-id="row"><td class="second"><input type="checkbox"></td></tr>'
      + '<tr data-id="row-expanded"><td><input type="checkbox"></td></tr>'
      + '<tr data-id="row"><td class="third"><input type="checkbox"></td></tr>'
      + '</tbody>';
    const all = Array.from({ length: 30 }, (_, index) => `R${index}`);

    it('should widen the change a select-all click makes to every row', () => {
      const selected = ref<string[] | undefined>([]);
      const { modelSelected, onClickCapture } = useWindowedSelectAll(selected, { all: ['A', 'B', 'C'], enabled: true, rendered: ['A'] });

      onClickCapture(clickOn('thead input', root));
      set(modelSelected, ['A']);

      expect(get(selected)).toStrictEqual(['A', 'B', 'C']);
    });

    it('should leave a row checkbox click as the table applied it', () => {
      const selected = ref<string[] | undefined>([]);
      const { modelSelected, onClickCapture } = useWindowedSelectAll(selected, { all: ['A', 'B', 'C'], enabled: true, rendered: ['A'] });

      onClickCapture(clickOn('tbody input', root));
      set(modelSelected, ['A']);

      expect(get(selected)).toStrictEqual(['A']);
    });

    it('should widen only the change right after the click', () => {
      const selected = ref<string[] | undefined>([]);
      const { modelSelected, onClickCapture } = useWindowedSelectAll(selected, { all: ['A', 'B', 'C'], enabled: true, rendered: ['A'] });

      onClickCapture(clickOn('thead input', root));
      set(modelSelected, ['A']);
      set(modelSelected, ['A', 'B', 'C', 'D']);
      set(modelSelected, ['B']);

      expect(get(selected)).toStrictEqual(['B']);
    });

    it('should not widen anything for a table that renders every row', () => {
      const selected = ref<string[] | undefined>([]);
      const { modelSelected, onClickCapture } = useWindowedSelectAll(selected, { all: ['A', 'B', 'C'], enabled: false, rendered: ['A', 'B', 'C'] });

      onClickCapture(clickOn('thead input', root));
      set(modelSelected, ['A']);

      expect(get(selected)).toStrictEqual(['A']);
    });

    it('should apply a shift-click range over every row, wherever the window has moved', () => {
      const selected = ref<string[] | undefined>(['R5']);
      const rendered = ref<string[]>(['R5']);
      const { onClickCapture } = useWindowedSelectAll(selected, { all, enabled: true, rendered });

      onClickCapture(clickOn('.first', windowRoot));
      set(rendered, ['R20', 'R21', 'R22']);
      const event = clickOn('.third', windowRoot, true);
      onClickCapture(event);

      expect(get(selected)).toStrictEqual(['R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17', 'R18', 'R19', 'R20', 'R21', 'R22']);
      expect(event.defaultPrevented).toBe(true);
    });

    it('should read the clicked row past an expanded row, and leave a plain click to the table', () => {
      const selected = ref<string[] | undefined>(['R21']);
      const { onClickCapture } = useWindowedSelectAll(selected, { all, enabled: true, rendered: ['R20', 'R21', 'R22'] });

      const plain = clickOn('.second', windowRoot);
      onClickCapture(plain);
      onClickCapture(clickOn('.third', windowRoot, true));

      expect(plain.defaultPrevented).toBe(false);
      expect(get(selected)).toStrictEqual(['R21', 'R22']);
    });

    it('should leave a shift-click outside a checkbox cell to the table', () => {
      const selected = ref<string[] | undefined>([]);
      const { onClickCapture } = useWindowedSelectAll(selected, { all, enabled: true, rendered: ['R20', 'R21', 'R22'] });

      onClickCapture(clickOn('.first', windowRoot));
      const event = clickOn('.name', windowRoot, true);
      onClickCapture(event);

      expect(event.defaultPrevented).toBe(false);
    });
  });

  describe('rangeSelection', () => {
    const all = ['A', 'B', 'C', 'D', 'E'];

    it('should give the rows between the two the anchor\'s state, in either direction', () => {
      expect(rangeSelection(['B'], all, 'B', 'D')).toStrictEqual(['B', 'C', 'D']);
      expect(rangeSelection(['D'], all, 'D', 'B')).toStrictEqual(['D', 'B', 'C']);
      expect(rangeSelection(['A', 'C', 'E'], all, 'B', 'D')).toStrictEqual(['A', 'E']);
    });

    it('should toggle the anchor on a shift-click on itself', () => {
      expect(rangeSelection(['B'], all, 'B', 'B')).toStrictEqual([]);
      expect(rangeSelection([], all, 'B', 'B')).toStrictEqual(['B']);
    });

    it('should leave the selection alone when either row is gone', () => {
      expect(rangeSelection(['B'], all, 'Z', 'D')).toStrictEqual(['B']);
    });
  });
});
