import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ChainInfo } from '@/modules/core/api/types/chains';
import type { Rule } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import { afterEach, describe, expect, it } from 'vitest';
import { effectScope, ref } from 'vue';
import { useRuleEditorForm, type UseRuleEditorFormReturn } from '@/modules/settings/general/disabled-chain-queries/use-rule-editor-form';

const ADDR_A = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
const ADDR_B = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65';

function addressAccount(chain: string, address: string): BlockchainAccount {
  return {
    chain,
    data: { address, type: 'address' },
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
} = {}): Harness {
  const editing = ref<Rule | undefined>(initial.editing);
  const scope = effectScope();
  const form = scope.run(() => useRuleEditorForm({
    accounts: initial.accounts ?? defaultAccounts,
    chains: initial.chains ?? defaultChains,
    editing,
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
      expect(harness.form.kind.value).toBe('chain');
      expect(harness.form.chainId.value).toBeUndefined();
      expect(harness.form.canSave.value).toBe(false);
    });

    it('should prefill from an editing chain rule', () => {
      harness = createHarness({
        editing: { chainId: 'optimism', id: 'r1', kind: 'chain' },
      });
      expect(harness.form.kind.value).toBe('chain');
      expect(harness.form.chainId.value).toBe('optimism');
      expect(harness.form.canSave.value).toBe(true);
    });

    it('should prefill scope=all when an editing address rule covers every tracked chain', () => {
      harness = createHarness({
        editing: { address: ADDR_A, chainIds: ['eth', 'optimism'], id: 'r2', kind: 'address' },
      });
      expect(harness.form.kind.value).toBe('address');
      expect(harness.form.address.value).toBe(ADDR_A);
      expect(harness.form.scope.value).toBe('all');
    });

    it('should prefill scope=specific when an editing address rule covers a subset', () => {
      harness = createHarness({
        editing: { address: ADDR_A, chainIds: ['optimism'], id: 'r3', kind: 'address' },
      });
      expect(harness.form.scope.value).toBe('specific');
      expect(harness.form.selectedChainIds.value).toEqual(['optimism']);
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

  describe('availableChainsForAddress', () => {
    it('should fall back to every chain when no address is picked', () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      expect([...harness.form.availableChainsForAddress.value].sort()).toEqual(
        ['arbitrum_one', 'eth', 'optimism'],
      );
    });

    it('should narrow to chains where the picked address is tracked', () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      harness.form.address.value = ADDR_B;
      expect(harness.form.availableChainsForAddress.value).toEqual(['eth']);
    });
  });

  describe('buildDraft', () => {
    it('should return undefined while the form is invalid', () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      expect(harness.form.buildDraft()).toBeUndefined();
    });

    it('should produce a chain draft', () => {
      harness = createHarness();
      harness.form.chainId.value = 'eth';
      expect(harness.form.buildDraft()).toEqual({ chainId: 'eth', kind: 'chain' });
    });

    it('should produce an address draft covering all tracked chains in scope=all', () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      harness.form.address.value = ADDR_A;
      harness.form.scope.value = 'all';
      const draft = harness.form.buildDraft();
      expect(draft).toEqual({
        address: ADDR_A,
        chainIds: expect.arrayContaining(['eth', 'optimism']),
        kind: 'address',
      });
    });

    it('should produce an address draft limited to selected chains in scope=specific', () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      harness.form.address.value = ADDR_A;
      harness.form.scope.value = 'specific';
      harness.form.selectedChainIds.value = ['optimism'];
      expect(harness.form.buildDraft()).toEqual({
        address: ADDR_A,
        chainIds: ['optimism'],
        kind: 'address',
      });
    });

    it('should require at least one chain in scope=specific', () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      harness.form.address.value = ADDR_A;
      harness.form.scope.value = 'specific';
      harness.form.selectedChainIds.value = [];
      expect(harness.form.canSave.value).toBe(false);
      expect(harness.form.buildDraft()).toBeUndefined();
    });
  });

  describe('reactive pruning', () => {
    it('should prune selected chains that no longer apply when the picked address changes', async () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      harness.form.scope.value = 'specific';
      harness.form.address.value = ADDR_A;
      harness.form.selectedChainIds.value = ['eth', 'optimism'];
      await nextTick();
      harness.form.address.value = ADDR_B;
      await nextTick();
      expect(harness.form.selectedChainIds.value).toEqual(['eth']);
    });
  });

  describe('reset', () => {
    it('should restore the original editing state, discarding edits', () => {
      harness = createHarness({
        editing: { chainId: 'eth', id: 'r1', kind: 'chain' },
      });
      harness.form.chainId.value = 'optimism';
      harness.form.reset();
      expect(harness.form.chainId.value).toBe('eth');
    });

    it('should clear all fields when editing is undefined', () => {
      harness = createHarness();
      harness.form.kind.value = 'address';
      harness.form.address.value = ADDR_A;
      harness.form.scope.value = 'specific';
      harness.form.selectedChainIds.value = ['eth'];
      harness.form.reset();
      expect(harness.form.kind.value).toBe('chain');
      expect(harness.form.address.value).toBeUndefined();
      expect(harness.form.selectedChainIds.value).toEqual([]);
      expect(harness.form.scope.value).toBe('all');
    });
  });
});
