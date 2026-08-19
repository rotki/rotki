import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ChainInfo } from '@/modules/core/api/types/chains';
import type { Rule } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import { afterEach, assert, describe, expect, it } from 'vitest';
import { effectScope, ref } from 'vue';
import { useRuleEditorForm, type UseRuleEditorFormReturn } from '@/modules/settings/general/disabled-chain-queries/use-rule-editor-form';

type AddressOption = UseRuleEditorFormReturn['addressOptions']['value'][number];

const ADDR_A = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
const ADDR_B = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65';

function addressAccount(chain: string, address: string, label?: string): BlockchainAccount {
  return {
    chain,
    data: { address, type: 'address' },
    label,
    nativeAsset: 'ETH',
  };
}

function validatorAccount(chain: string, publicKey: string): BlockchainAccount {
  return {
    chain,
    data: { index: 1, publicKey, status: 'active', type: 'validator' },
    nativeAsset: 'ETH',
  };
}

const defaultChains: ChainInfo[] = [
  { evmChainName: 'ethereum', id: 'eth', image: '', name: 'Ethereum', nativeToken: 'ETH', type: 'evm' },
  { evmChainName: 'optimism', id: 'optimism', image: '', name: 'Optimism', nativeToken: 'ETH', type: 'evm' },
  { evmChainName: 'arbitrum_one', id: 'arbitrum_one', image: '', name: 'Arbitrum One', nativeToken: 'ETH', type: 'evm' },
];

const defaultAccounts: Record<string, BlockchainAccount[]> = {
  eth: [addressAccount('eth', ADDR_A), addressAccount('eth', ADDR_B), validatorAccount('eth', '0xpubkey')],
  optimism: [addressAccount('optimism', ADDR_A)],
};

interface Harness {
  form: UseRuleEditorFormReturn;
  editing: ReturnType<typeof ref<Rule | undefined>>;
  dispose: () => void;
}

function createHarness(initial: {
  editing?: Rule;
  accounts?: Record<string, BlockchainAccount[]>;
  chains?: ChainInfo[];
  resolveName?: (address: string, chainId?: string) => string | undefined;
} = {}): Harness {
  const editing = ref<Rule | undefined>(initial.editing);
  const scope = effectScope();
  const form = scope.run(() => useRuleEditorForm({
    accounts: initial.accounts ?? defaultAccounts,
    chains: initial.chains ?? defaultChains,
    editing,
    resolveName: initial.resolveName,
  }))!;
  return {
    dispose: (): void => scope.stop(),
    editing,
    form,
  };
}

describe('useRuleEditorForm', () => {
  let harness: Harness;

  afterEach(() => harness?.dispose());

  describe('initial state', () => {
    it('should default to chain kind with nothing selected', () => {
      harness = createHarness();
      expect(harness.form.modelKind.value).toBe('chain');
      expect(harness.form.modelChainId.value).toBeUndefined();
      expect(harness.form.canSave.value).toBe(false);
    });

    it('should prefill from an editing chain rule', () => {
      harness = createHarness({
        editing: { chainId: 'optimism', id: 'r1', kind: 'chain' },
      });
      expect(harness.form.modelKind.value).toBe('chain');
      expect(harness.form.modelChainId.value).toBe('optimism');
      expect(harness.form.canSave.value).toBe(true);
    });

    it('should prefill scope=all when an editing address rule covers every tracked chain', () => {
      harness = createHarness({
        editing: { address: ADDR_A, chainIds: ['eth', 'optimism'], id: 'r2', kind: 'address' },
      });
      expect(harness.form.modelKind.value).toBe('address');
      expect(harness.form.modelAddress.value).toBe(ADDR_A);
      expect(harness.form.modelScope.value).toBe('all');
    });

    it('should prefill scope=specific when an editing address rule covers a subset', () => {
      harness = createHarness({
        editing: { address: ADDR_A, chainIds: ['optimism'], id: 'r3', kind: 'address' },
      });
      expect(harness.form.modelScope.value).toBe('specific');
      expect(harness.form.modelSelectedChainIds.value).toEqual(['optimism']);
    });
  });

  describe('addressOptions', () => {
    it('should list each tracked address once with the chains it appears on', () => {
      harness = createHarness();
      const options = harness.form.addressOptions.value;
      expect(options.map(o => o.address).sort()).toEqual([ADDR_A, ADDR_B].sort());
      const a = options.find(o => o.address === ADDR_A);
      expect(a && [...a.chainIds].sort()).toEqual(['eth', 'optimism']);
    });

    it('should ignore validator accounts', () => {
      harness = createHarness();
      const options = harness.form.addressOptions.value;
      expect(options.find(o => o.address === '0xpubkey')).toBeUndefined();
    });
  });

  describe('filterAddressOption', () => {
    function optionFor(address: string): AddressOption {
      const option = harness.form.addressOptions.value.find(o => o.address === address);
      assert(option);
      return option;
    }

    it('should match a fragment of the address, case-insensitively', () => {
      harness = createHarness();
      const { filterAddressOption } = harness.form;
      expect(filterAddressOption(optionFor(ADDR_A), ADDR_A.slice(10, 20).toUpperCase())).toBe(true);
      expect(filterAddressOption(optionFor(ADDR_B), ADDR_A.slice(10, 20))).toBe(false);
    });

    it('should match the account label', () => {
      harness = createHarness({
        accounts: {
          eth: [addressAccount('eth', ADDR_A, 'My Ledger'), addressAccount('eth', ADDR_B)],
        },
      });
      const { filterAddressOption } = harness.form;
      expect(filterAddressOption(optionFor(ADDR_A), 'ledger')).toBe(true);
      expect(filterAddressOption(optionFor(ADDR_B), 'ledger')).toBe(false);
    });

    it('should match the resolved alias name', () => {
      harness = createHarness({
        resolveName: (address: string): string | undefined => address === ADDR_A ? 'rotki.eth' : undefined,
      });
      const { filterAddressOption } = harness.form;
      expect(filterAddressOption(optionFor(ADDR_A), 'rotki')).toBe(true);
      expect(filterAddressOption(optionFor(ADDR_B), 'rotki')).toBe(false);
    });

    it('should keep every option for an empty query', () => {
      harness = createHarness();
      const { filterAddressOption } = harness.form;
      expect(filterAddressOption(optionFor(ADDR_A), '  ')).toBe(true);
    });
  });

  describe('availableChainsForAddress', () => {
    it('should fall back to every chain when no address is picked', () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      expect([...harness.form.availableChainsForAddress.value].sort()).toEqual(
        ['arbitrum_one', 'eth', 'optimism'],
      );
    });

    it('should narrow to chains where the picked address is tracked', () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      harness.form.modelAddress.value = ADDR_B;
      expect(harness.form.availableChainsForAddress.value).toEqual(['eth']);
    });
  });

  describe('buildDraft', () => {
    it('should return undefined while the form is invalid', () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      expect(harness.form.buildDraft()).toBeUndefined();
    });

    it('should produce a chain draft', () => {
      harness = createHarness();
      harness.form.modelChainId.value = 'eth';
      expect(harness.form.buildDraft()).toEqual({ chainId: 'eth', kind: 'chain' });
    });

    it('should produce an address draft covering all tracked chains in scope=all', () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      harness.form.modelAddress.value = ADDR_A;
      harness.form.modelScope.value = 'all';
      const draft = harness.form.buildDraft();
      expect(draft).toEqual({
        address: ADDR_A,
        chainIds: expect.arrayContaining(['eth', 'optimism']),
        kind: 'address',
      });
    });

    it('should produce an address draft limited to selected chains in scope=specific', () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      harness.form.modelAddress.value = ADDR_A;
      harness.form.modelScope.value = 'specific';
      harness.form.modelSelectedChainIds.value = ['optimism'];
      expect(harness.form.buildDraft()).toEqual({
        address: ADDR_A,
        chainIds: ['optimism'],
        kind: 'address',
      });
    });

    it('should require at least one chain in scope=specific', () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      harness.form.modelAddress.value = ADDR_A;
      harness.form.modelScope.value = 'specific';
      harness.form.modelSelectedChainIds.value = [];
      expect(harness.form.canSave.value).toBe(false);
      expect(harness.form.buildDraft()).toBeUndefined();
    });
  });

  describe('reactive pruning', () => {
    it('should prune selected chains that no longer apply when the picked address changes', async () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      harness.form.modelScope.value = 'specific';
      harness.form.modelAddress.value = ADDR_A;
      harness.form.modelSelectedChainIds.value = ['eth', 'optimism'];
      await nextTick();
      harness.form.modelAddress.value = ADDR_B;
      await nextTick();
      expect(harness.form.modelSelectedChainIds.value).toEqual(['eth']);
    });
  });

  describe('reset', () => {
    it('should restore the original editing state, discarding edits', () => {
      harness = createHarness({
        editing: { chainId: 'eth', id: 'r1', kind: 'chain' },
      });
      harness.form.modelChainId.value = 'optimism';
      harness.form.reset();
      expect(harness.form.modelChainId.value).toBe('eth');
    });

    it('should clear all fields when editing is undefined', () => {
      harness = createHarness();
      harness.form.modelKind.value = 'address';
      harness.form.modelAddress.value = ADDR_A;
      harness.form.modelScope.value = 'specific';
      harness.form.modelSelectedChainIds.value = ['eth'];
      harness.form.reset();
      expect(harness.form.modelKind.value).toBe('chain');
      expect(harness.form.modelAddress.value).toBeUndefined();
      expect(harness.form.modelSelectedChainIds.value).toEqual([]);
      expect(harness.form.modelScope.value).toBe('all');
    });
  });
});
