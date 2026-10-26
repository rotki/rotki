import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useListHighlight } from '@/modules/core/common/use-list-highlight';

/**
 * Builds a keyboard event for one key, with composition explicitly off.
 *
 * @remarks
 * `isComposing: false` has to be stated. `createMock` answers any property it was not given with
 * an auto-stub, which is truthy, so omitting it makes every key look like it arrived mid-IME
 * composition and the handler under test returns before doing anything.
 */
function key(name: string, isComposing = false): KeyboardEvent {
  return createMock<KeyboardEvent>({ isComposing, key: name, preventDefault: vi.fn() });
}

function move(clientX: number, clientY: number): MouseEvent {
  return createMock<MouseEvent>({ clientX, clientY });
}

describe('useListHighlight', () => {
  const onSelect = vi.fn<(item: string) => void>();
  const onClose = vi.fn<() => void>();
  const scrollTo = vi.fn<(index: number) => void>();

  function setup(items: MaybeRefOrGetter<string[]>, firstSelectable?: MaybeRefOrGetter<number>): ReturnType<typeof useListHighlight<string>> {
    return useListHighlight(items, { firstSelectable, keyOf: item => item, onClose, onSelect, scrollTo });
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should start on the first row', () => {
    const { highlighted } = setup(['A', 'B']);

    expect(get(highlighted)).toBe(0);
  });

  it('should move down and scroll the highlighted row into view, since the list is virtualized', () => {
    const { highlighted, onKeydown } = setup(['A', 'B', 'C']);

    onKeydown(key('ArrowDown'));

    expect(get(highlighted)).toBe(1);
    expect(scrollTo).toHaveBeenCalledWith(1);
  });

  it('should wrap from the last row to the first', () => {
    const { highlighted, onKeydown } = setup(['A', 'B']);

    onKeydown(key('ArrowDown'));
    onKeydown(key('ArrowDown'));

    expect(get(highlighted)).toBe(0);
  });

  it('should wrap backwards from the first row to the last', () => {
    const { highlighted, onKeydown } = setup(['A', 'B', 'C']);

    onKeydown(key('ArrowUp'));

    expect(get(highlighted)).toBe(2);
  });

  it('should commit the highlighted row on enter', () => {
    const { onKeydown } = setup(['A', 'B']);

    onKeydown(key('ArrowDown'));
    onKeydown(key('Enter'));

    expect(onSelect).toHaveBeenCalledWith('B');
  });

  it('should close on escape, even with nothing to pick', () => {
    const { onKeydown } = setup([]);

    onKeydown(key('Escape'));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('should neither move nor commit on an empty list', () => {
    const { highlighted, onKeydown } = setup([]);

    onKeydown(key('ArrowDown'));
    onKeydown(key('Enter'));

    expect(get(highlighted)).toBe(0);
    expect(onSelect).not.toHaveBeenCalled();
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('should put the highlight on a given row and scroll to it', () => {
    const { highlightAt, highlighted } = setup(['A', 'B', 'C']);

    highlightAt(2);

    expect(get(highlighted)).toBe(2);
    expect(scrollTo).toHaveBeenCalledWith(2);
  });

  it('should follow the pointer to a hovered row without scrolling, since the row is already under the cursor', () => {
    const { highlighted, onPointerMove } = setup(['A', 'B', 'C']);

    onPointerMove(move(10, 10), 2);

    expect(get(highlighted)).toBe(2);
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('should ignore a pointer move on a row index outside the list', () => {
    const { highlighted, onPointerMove } = setup(['A', 'B']);

    onPointerMove(move(10, 10), 7);

    expect(get(highlighted)).toBe(0);
  });

  it('should ignore a row that slid under a still cursor', () => {
    const { highlighted, onKeydown, onPointerMove } = setup(['A', 'B', 'C']);

    onPointerMove(move(10, 10), 0);
    onKeydown(key('ArrowDown'));
    expect(get(highlighted)).toBe(1);

    onPointerMove(move(10, 10), 2);

    expect(get(highlighted)).toBe(1);
  });

  it('should let the keyboard walk the list without the pointer stealing it back', () => {
    const { highlighted, onKeydown, onPointerMove } = setup(['A', 'B', 'C', 'D', 'E']);
    onPointerMove(move(10, 10), 0);

    for (const slidUnderCursor of [2, 3, 4]) {
      onKeydown(key('ArrowDown'));
      onPointerMove(move(10, 10), slidUnderCursor);
    }

    expect(get(highlighted)).toBe(3);
  });

  it('should hand control back once the pointer genuinely moves', () => {
    const { highlighted, onKeydown, onPointerMove } = setup(['A', 'B', 'C']);
    onPointerMove(move(10, 10), 0);
    onKeydown(key('ArrowDown'));

    onPointerMove(move(10, 40), 2);

    expect(get(highlighted)).toBe(2);
  });

  it('should leave every key to an IME that is composing, escape included', () => {
    const { highlighted, onKeydown } = setup(['A', 'B']);

    for (const name of ['ArrowDown', 'Enter', 'Escape'])
      onKeydown(key(name, true));

    expect(get(highlighted)).toBe(0);
    expect(onSelect).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();

    onKeydown(key('Escape'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('should reset to the first result when the list contents change', async () => {
    const items = ref<string[]>(['A', 'B', 'C']);
    const { highlighted, onKeydown } = setup(items);
    onKeydown(key('ArrowDown'));

    set(items, ['B']);
    await nextTick();

    expect(get(highlighted)).toBe(0);
  });

  it('should hold the highlight when the list is only reordered, since picking a value can pin it without changing the rows on offer', async () => {
    const items = ref<string[]>(['A', 'B', 'C']);
    const { highlighted, onKeydown } = setup(items);
    onKeydown(key('ArrowDown'));
    scrollTo.mockClear();

    set(items, ['C', 'A', 'B']);
    await nextTick();

    expect(get(highlighted)).toBe(1);
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('should reset past the rows before the first selectable one, so enter picks a result rather than a pinned row', async () => {
    const items = ref<string[]>(['A', 'B']);
    const { highlighted } = setup(items, 1);

    set(items, ['A', 'C', 'D']);
    await nextTick();

    expect(get(highlighted)).toBe(1);
    expect(scrollTo).toHaveBeenLastCalledWith(1);
  });

  it('should reset to the first row when the rows before the first selectable one are all there is', async () => {
    const items = ref<string[]>(['A', 'B']);
    const { highlighted, onKeydown } = setup(items, 5);
    onKeydown(key('ArrowDown'));

    set(items, ['C']);
    await nextTick();

    expect(get(highlighted)).toBe(0);
  });
});
