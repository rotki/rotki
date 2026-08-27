import type { TradeAssetOption } from '@/modules/wallet/send/use-trade-asset-options';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeAssetNavigation } from './use-trade-asset-navigation';

function option(identifier: string, chain = 'eth'): TradeAssetOption {
  return {
    address: '',
    ambiguous: false,
    asset: { amount: bigNumberify(1), asset: identifier, chain },
    name: identifier,
    symbol: identifier,
  };
}

/**
 * Builds a keyboard event for one key, with composition explicitly off.
 *
 * @remarks
 * `isComposing: false` has to be stated. `createMock` answers any property it was not given with
 * an auto-stub, which is truthy, so omitting it makes every key look like it arrived mid-IME
 * composition and the handler under test returns before doing anything.
 */
function key(name: string): KeyboardEvent {
  return createMock<KeyboardEvent>({ isComposing: false, key: name, preventDefault: vi.fn() });
}

function move(clientX: number, clientY: number): MouseEvent {
  return createMock<MouseEvent>({ clientX, clientY });
}

describe('useTradeAssetNavigation', () => {
  const onSelect = vi.fn();
  const onClose = vi.fn();
  const scrollTo = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should start on the first row', () => {
    const { highlighted } = useTradeAssetNavigation([option('A'), option('B')], { onClose, onSelect, scrollTo });

    expect(get(highlighted)).toBe(0);
  });

  it('should move down and scroll the highlighted row into view', () => {
    const { highlighted, onKeydown } = useTradeAssetNavigation(
      [option('A'), option('B'), option('C')],
      { onClose, onSelect, scrollTo },
    );

    onKeydown(key('ArrowDown'));

    expect(get(highlighted)).toBe(1);
    // Virtualized, so moving the highlight without scrolling would point at an off-screen row.
    expect(scrollTo).toHaveBeenCalledWith(1);
  });

  it('should wrap from the last row to the first', () => {
    const { highlighted, onKeydown } = useTradeAssetNavigation(
      [option('A'), option('B')],
      { onClose, onSelect, scrollTo },
    );

    onKeydown(key('ArrowDown'));
    onKeydown(key('ArrowDown'));

    expect(get(highlighted)).toBe(0);
  });

  it('should wrap backwards from the first row to the last', () => {
    const { highlighted, onKeydown } = useTradeAssetNavigation(
      [option('A'), option('B'), option('C')],
      { onClose, onSelect, scrollTo },
    );

    onKeydown(key('ArrowUp'));

    expect(get(highlighted)).toBe(2);
  });

  it('should commit the highlighted row on enter', () => {
    const items = [option('A'), option('B')];
    const { onKeydown } = useTradeAssetNavigation(items, { onClose, onSelect, scrollTo });

    onKeydown(key('ArrowDown'));
    onKeydown(key('Enter'));

    expect(onSelect).toHaveBeenCalledWith(items[1]);
  });

  it('should close on escape', () => {
    const { onKeydown } = useTradeAssetNavigation([option('A')], { onClose, onSelect, scrollTo });

    onKeydown(key('Escape'));

    expect(onClose).toHaveBeenCalled();
  });

  it('should close on escape even with nothing to pick', () => {
    const { onKeydown } = useTradeAssetNavigation([], { onClose, onSelect, scrollTo });

    onKeydown(key('Escape'));

    expect(onClose).toHaveBeenCalled();
  });

  it('should do nothing on enter when the list is empty', () => {
    const { onKeydown } = useTradeAssetNavigation([], { onClose, onSelect, scrollTo });

    onKeydown(key('Enter'));
    onKeydown(key('ArrowDown'));

    expect(onSelect).not.toHaveBeenCalled();
  });

  it('should highlight a given identifier and scroll to it', () => {
    const { highlight, highlighted } = useTradeAssetNavigation(
      [option('A'), option('B'), option('C')],
      { onClose, onSelect, scrollTo },
    );

    highlight('C', 'eth');

    expect(get(highlighted)).toBe(2);
    expect(scrollTo).toHaveBeenCalledWith(2);
  });

  it('should match the highlighted row on chain as well as identifier', () => {
    const { highlight, highlighted } = useTradeAssetNavigation(
      [option('ETH', 'eth'), option('USDC', 'eth'), option('ETH', 'base')],
      { onClose, onSelect, scrollTo },
    );

    highlight('ETH', 'base');

    expect(get(highlighted)).toBe(2);
  });

  it('should fall back to the first row for an identifier not in the list', () => {
    const { highlight, highlighted } = useTradeAssetNavigation(
      [option('A'), option('B')],
      { onClose, onSelect, scrollTo },
    );

    highlight('NOT_THERE', 'eth');

    expect(get(highlighted)).toBe(0);
  });

  it('should follow the pointer to a hovered row without scrolling', () => {
    const { highlighted, onPointerMove } = useTradeAssetNavigation(
      [option('A'), option('B'), option('C')],
      { onClose, onSelect, scrollTo },
    );

    onPointerMove(move(10, 10), 2);

    expect(get(highlighted)).toBe(2);
    // The row is already under the cursor; scrolling to it would shift the list out from under it.
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('should ignore a pointer move on a row index outside the list', () => {
    const { highlighted, onPointerMove } = useTradeAssetNavigation(
      [option('A'), option('B')],
      { onClose, onSelect, scrollTo },
    );

    onPointerMove(move(10, 10), 7);

    expect(get(highlighted)).toBe(0);
  });

  it('should ignore a row that slid under a still cursor', () => {
    const { highlighted, onKeydown, onPointerMove } = useTradeAssetNavigation(
      [option('A'), option('B'), option('C')],
      { onClose, onSelect, scrollTo },
    );

    onPointerMove(move(10, 10), 0);
    onKeydown(key('ArrowDown'));
    expect(get(highlighted)).toBe(1);

    onPointerMove(move(10, 10), 2);

    expect(get(highlighted)).toBe(1);
  });

  it('should let the keyboard walk the list without the pointer stealing it back', () => {
    const { highlighted, onKeydown, onPointerMove } = useTradeAssetNavigation(
      [option('A'), option('B'), option('C'), option('D'), option('E')],
      { onClose, onSelect, scrollTo },
    );
    onPointerMove(move(10, 10), 0);

    for (const slidUnderCursor of [2, 3, 4]) {
      onKeydown(key('ArrowDown'));
      onPointerMove(move(10, 10), slidUnderCursor);
    }

    expect(get(highlighted)).toBe(3);
  });

  it('should hand control back once the pointer genuinely moves', () => {
    const { highlighted, onKeydown, onPointerMove } = useTradeAssetNavigation(
      [option('A'), option('B'), option('C')],
      { onClose, onSelect, scrollTo },
    );
    onPointerMove(move(10, 10), 0);
    onKeydown(key('ArrowDown'));

    onPointerMove(move(10, 40), 2);

    expect(get(highlighted)).toBe(2);
  });

  it('should ignore keys while an IME is composing', () => {
    const items = [option('A'), option('B')];
    const { highlighted, onKeydown } = useTradeAssetNavigation(items, { onClose, onSelect, scrollTo });

    onKeydown(createMock<KeyboardEvent>({ isComposing: true, key: 'ArrowDown', preventDefault: vi.fn() }));
    onKeydown(createMock<KeyboardEvent>({ isComposing: true, key: 'Enter', preventDefault: vi.fn() }));

    expect(get(highlighted)).toBe(0);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('should reset to the first result when the list contents change', async () => {
    const items = ref<TradeAssetOption[]>([option('A'), option('B'), option('C')]);
    const { highlighted, onKeydown } = useTradeAssetNavigation(items, { onClose, onSelect, scrollTo });
    onKeydown(key('ArrowDown'));
    expect(get(highlighted)).toBe(1);

    set(items, [option('B')]);
    await nextTick();

    expect(get(highlighted)).toBe(0);
  });

  it('should hold the highlight when the list is reordered but holds the same options', async () => {
    const items = ref<TradeAssetOption[]>([option('A'), option('B'), option('C')]);
    const { highlighted, onKeydown } = useTradeAssetNavigation(items, { onClose, onSelect, scrollTo });
    onKeydown(key('ArrowDown'));
    scrollTo.mockClear();

    // A balances tick rebuilds the array. Same contents, so the highlight must not jump.
    set(items, [option('C'), option('A'), option('B')]);
    await nextTick();

    expect(get(highlighted)).toBe(1);
    expect(scrollTo).not.toHaveBeenCalled();
  });
});
