import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountCategoryHelper } from './use-account-category-helper';

const h = vi.hoisted(() => ({
  supportedChains: [
    { id: 'eth', type: 'evm' },
    { id: 'optimism', type: 'evm' },
    { id: 'zksync_lite', type: 'evmlike' },
    { id: 'btc', type: 'bitcoin' },
  ],
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const vue = await import('vue');
  return { useSupportedChains: vi.fn(() => ({ supportedChains: vue.ref(h.supportedChains) })) };
});

describe('useAccountCategoryHelper', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should flag the evm category and include evm plus evmlike chains', () => {
    const { chainIds, isEvm } = useAccountCategoryHelper('evm');
    expect(get(isEvm)).toBe(true);
    expect(get(chainIds)).toEqual(['eth', 'optimism', 'zksync_lite']);
  });

  it('should return only the matching chains for a non-evm category', () => {
    const { chainIds, isEvm } = useAccountCategoryHelper('bitcoin');
    expect(get(isEvm)).toBe(false);
    expect(get(chainIds)).toEqual(['btc']);
  });

  it('should react to a changing category getter', () => {
    const category = ref<string>('bitcoin');
    const { chainIds, isEvm } = useAccountCategoryHelper(category);
    expect(get(isEvm)).toBe(false);
    expect(get(chainIds)).toEqual(['btc']);

    set(category, 'evm');
    expect(get(isEvm)).toBe(true);
    expect(get(chainIds)).toEqual(['eth', 'optimism', 'zksync_lite']);
  });
});
