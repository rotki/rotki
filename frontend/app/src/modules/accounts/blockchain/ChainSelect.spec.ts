import type { SupportedChains } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createRuiPlugin } from '@/plugins/rui';
import '@test/i18n';

/**
 * Deliberately unsorted, and not in the order the backend happens to return them, so a spec that
 * passes only because the source list was already alphabetical cannot exist.
 */
const chains: SupportedChains = [
  { evmChainName: 'optimism', id: 'optimism', image: 'optimism.svg', name: 'Optimism', type: 'evm' },
  { evmChainName: 'ethereum', id: Blockchain.ETH, image: 'ethereum.svg', name: 'Ethereum', type: 'evm' },
  { id: Blockchain.BTC, image: 'btc.svg', name: 'Bitcoin', type: 'bitcoin' },
  { evmChainName: 'arbitrum_one', id: 'arbitrum_one', image: 'arbitrum.svg', name: 'Arbitrum One', type: 'evm' },
  { id: Blockchain.ETH2, image: 'eth.svg', name: 'Eth2', type: 'evm' },
];

const evmChains: string[] = ['optimism', Blockchain.ETH, 'arbitrum_one'];

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    isEvm: (chain: string): boolean => evmChains.includes(chain),
    supportedChains: computed<SupportedChains>(() => chains),
  }),
}));

const eth2Enabled = ref(true);

vi.mock('@/modules/session/use-module-enabled', async () => {
  const { Module } = await vi.importActual<typeof import('@/modules/core/common/modules')>(
    '@/modules/core/common/modules',
  );

  return {
    getModuleEnabled: (): boolean => get(eth2Enabled),
    Module,
  };
});

const ChainSelect = (await import('@/modules/accounts/blockchain/ChainSelect.vue')).default;

/** Renders the chain id as text, so the rendered option list can be read as ids. */
const ChainDisplayStub = defineComponent({
  props: {
    chain: { required: true, type: String },
    dense: { default: false, type: Boolean },
  },
  template: '<span class="chain-option">{{ chain }}</span>',
});

interface MountProps {
  evmOnly?: boolean;
  excludeEthStaking?: boolean;
  items?: string[];
}

/**
 * Mounts the select with the real `RuiAutoComplete`.
 *
 * The globally stubbed autocomplete neither orders nor filters its options, and those two are what
 * this spec is about. The real one teleports its menu to the body, so `Teleport` is stubbed to keep
 * the menu inside the wrapper.
 */
function createWrapper(props: MountProps = {}): VueWrapper<any> {
  return mount(ChainSelect, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        ChainDisplay: ChainDisplayStub,
        RuiAutoComplete: false,
        Teleport: true,
        Transition: false,
        TransitionGroup: false,
      },
    },
    props: {
      modelValue: undefined,
      ...props,
    },
  });
}

/** The option ids currently rendered in the menu, in render order. */
function renderedOptions(wrapper: VueWrapper<any>): string[] {
  return wrapper.findAll('[data-id=content] .chain-option').map(node => node.text());
}

async function open(wrapper: VueWrapper<any>): Promise<void> {
  await wrapper.find('[data-id=activator]').trigger('click');
  await vi.advanceTimersToNextTimerAsync();
}

async function search(wrapper: VueWrapper<any>, term: string): Promise<void> {
  await wrapper.find('input[type=text]').setValue(term);
  // `useAutoCompleteSearch` debounces the query before it filters.
  await vi.runOnlyPendingTimersAsync();
}

describe('accounts/blockchain/ChainSelect.vue', () => {
  let wrapper: VueWrapper<any>;

  beforeEach(() => {
    set(eth2Enabled, true);
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  describe('ordering', () => {
    it('sorts the chains alphabetically by their displayed name', async () => {
      wrapper = createWrapper();
      await open(wrapper);

      // "Eth2" sorts ahead of "Ethereum": the collator orders the digit before the letter.
      expect(renderedOptions(wrapper)).toEqual([
        'arbitrum_one',
        Blockchain.BTC,
        Blockchain.ETH2,
        Blockchain.ETH,
        'optimism',
      ]);
    });

    it('keeps the all-supported entry first, ahead of the sorted chains', async () => {
      wrapper = createWrapper({ items: ['all', 'optimism', Blockchain.ETH, 'arbitrum_one'] });
      await open(wrapper);

      expect(renderedOptions(wrapper)).toEqual(['all', 'arbitrum_one', Blockchain.ETH, 'optimism']);
    });

    it('sorts what is left after the evm-only and eth-staking filters', async () => {
      set(eth2Enabled, false);
      wrapper = createWrapper({ evmOnly: true });
      await open(wrapper);

      expect(renderedOptions(wrapper)).toEqual(['arbitrum_one', Blockchain.ETH, 'optimism']);
    });
  });

  describe('search', () => {
    it('narrows the options by chain name', async () => {
      wrapper = createWrapper();
      await open(wrapper);
      await search(wrapper, 'arbitrum');

      expect(renderedOptions(wrapper)).toEqual(['arbitrum_one']);
    });

    it('narrows the options by chain id', async () => {
      wrapper = createWrapper();
      await open(wrapper);
      await search(wrapper, 'optim');

      expect(renderedOptions(wrapper)).toEqual(['optimism']);
    });

    it('matches the all-supported entry on its label, not only on its id', async () => {
      wrapper = createWrapper({ items: ['all', 'optimism', Blockchain.ETH] });
      await open(wrapper);
      // The test translator returns the key, so the label carries "supported" as the real one does.
      await search(wrapper, 'supported');

      expect(renderedOptions(wrapper)).toEqual(['all']);
    });
  });
});
