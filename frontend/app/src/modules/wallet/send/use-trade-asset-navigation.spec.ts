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

/** The keyboard, pointer and reset behaviour is `useListHighlight`'s, pinned in its own spec. */
describe('useTradeAssetNavigation', () => {
  const onSelect = vi.fn();
  const onClose = vi.fn();
  const scrollTo = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should commit the highlighted option on enter', () => {
    const items = [option('A'), option('B')];
    const { onKeydown } = useTradeAssetNavigation(items, { onClose, onSelect, scrollTo });

    onKeydown(key('ArrowDown'));
    onKeydown(key('Enter'));

    expect(onSelect).toHaveBeenCalledWith(items[1]);
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

  it('should treat the same token on another chain as a new list, so the highlight resets rather than land on a different network', async () => {
    const items = ref<TradeAssetOption[]>([option('ETH', 'eth'), option('USDC', 'eth')]);
    const { highlighted, onKeydown } = useTradeAssetNavigation(items, { onClose, onSelect, scrollTo });
    onKeydown(key('ArrowDown'));

    set(items, [option('ETH', 'base'), option('USDC', 'base')]);
    await nextTick();

    expect(get(highlighted)).toBe(0);
  });
});
