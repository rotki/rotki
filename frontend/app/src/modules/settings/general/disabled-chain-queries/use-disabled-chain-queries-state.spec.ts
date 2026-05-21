import flushPromises from 'flush-promises';
import { afterEach, describe, expect, it } from 'vitest';
import { effectScope, ref, type Ref } from 'vue';
import {
  type DisabledChainQueries,
  type Rule,
  useDisabledChainQueriesState,
  type UseDisabledChainQueriesStateReturn,
} from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';

const ADDR_A = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
const ADDR_B = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65';

function identityMatcher(raw: string): string | undefined {
  return raw === 'not_a_real_chain' ? undefined : raw;
}

interface Harness {
  state: UseDisabledChainQueriesStateReturn;
  source: Ref<DisabledChainQueries>;
  ready: Ref<boolean>;
  dispose: () => void;
}

function createHarness(initial: {
  source?: DisabledChainQueries;
  ready?: boolean;
  matchChain?: (raw: string) => string | undefined;
} = {}): Harness {
  const source = ref<DisabledChainQueries>(initial.source ?? {});
  const ready = ref<boolean>(initial.ready ?? true);
  const scope = effectScope();
  const state = scope.run(() => useDisabledChainQueriesState({
    matchChain: initial.matchChain ?? identityMatcher,
    ready,
    source,
  }))!;
  return {
    dispose: (): void => scope.stop(),
    ready,
    source,
    state,
  };
}

function findRule(rules: readonly Rule[], predicate: (r: Rule) => boolean): Rule {
  const found = rules.find(predicate);
  if (!found)
    throw new Error('rule not found');
  return found;
}

describe('useDisabledChainQueriesState', () => {
  let harness: Harness;

  afterEach(() => {
    harness?.dispose();
  });

  describe('initial sync', () => {
    it('should not touch local state until ready', async () => {
      harness = createHarness({ ready: false, source: { eth: [ADDR_A] } });
      await flushPromises();
      expect(harness.state.rules.value).toEqual([]);
    });

    it('should produce a chain rule for an empty-list chain', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();
      expect(harness.state.rules.value).toHaveLength(1);
      expect(harness.state.rules.value[0]).toMatchObject({ chainId: 'eth', kind: 'chain' });
    });

    it('should produce one address rule per address, grouping chains', async () => {
      harness = createHarness({ source: { eth: [ADDR_A], optimism: [ADDR_A, ADDR_B] } });
      await flushPromises();
      const rules = harness.state.rules.value;
      const a = findRule(rules, r => r.kind === 'address' && r.address === ADDR_A);
      const b = findRule(rules, r => r.kind === 'address' && r.address === ADDR_B);
      expect(a.kind === 'address' && [...a.chainIds].sort()).toEqual(['eth', 'optimism']);
      expect(b.kind === 'address' && b.chainIds).toEqual(['optimism']);
    });

    it('should skip unsupported chains during sync', async () => {
      harness = createHarness({ source: { not_a_real_chain: [] } });
      await flushPromises();
      expect(harness.state.rules.value).toEqual([]);
    });
  });

  describe('addRule', () => {
    it('should add a chain rule and commit { chain: [] }', async () => {
      harness = createHarness({ source: {} });
      await flushPromises();
      const payload = harness.state.addRule({ chainId: 'eth', kind: 'chain' });
      expect(payload).toEqual({ eth: [] });
    });

    it('should add an address rule across multiple chains', async () => {
      harness = createHarness({ source: {} });
      await flushPromises();
      const payload = harness.state.addRule({
        address: ADDR_A,
        chainIds: ['eth', 'optimism'],
        kind: 'address',
      });
      expect(payload).toEqual({ eth: [ADDR_A], optimism: [ADDR_A] });
    });

    it('should auto-merge address rules for the same address', async () => {
      harness = createHarness({ source: {} });
      await flushPromises();
      harness.state.addRule({ address: ADDR_A, chainIds: ['eth'], kind: 'address' });
      harness.state.addRule({ address: ADDR_A, chainIds: ['optimism'], kind: 'address' });
      const addressRules = harness.state.rules.value.filter(r => r.kind === 'address');
      expect(addressRules).toHaveLength(1);
      expect(addressRules[0].kind === 'address' && [...addressRules[0].chainIds].sort()).toEqual(['eth', 'optimism']);
    });

    it('should drop address contributions on a chain that has a full-chain rule', async () => {
      harness = createHarness({ source: {} });
      await flushPromises();
      harness.state.addRule({ chainId: 'eth', kind: 'chain' });
      const payload = harness.state.addRule({
        address: ADDR_A,
        chainIds: ['eth', 'optimism'],
        kind: 'address',
      });
      expect(payload).toEqual({ eth: [], optimism: [ADDR_A] });
    });
  });

  describe('updateRule', () => {
    it('should replace a rule in place', async () => {
      harness = createHarness({ source: { eth: [ADDR_A] } });
      await flushPromises();
      const rule = findRule(harness.state.rules.value, r => r.kind === 'address');
      const payload = harness.state.updateRule(rule.id, {
        address: ADDR_A,
        chainIds: ['optimism'],
        kind: 'address',
      });
      expect(payload).toEqual({ optimism: [ADDR_A] });
    });

    it('should return undefined for an unknown id', async () => {
      harness = createHarness({ source: {} });
      await flushPromises();
      expect(harness.state.updateRule('missing', { chainId: 'eth', kind: 'chain' })).toBeUndefined();
    });
  });

  describe('removeRule', () => {
    it('should remove the rule and commit the new payload', async () => {
      harness = createHarness({ source: { eth: [], optimism: [ADDR_A] } });
      await flushPromises();
      const chainRule = findRule(harness.state.rules.value, r => r.kind === 'chain');
      const payload = harness.state.removeRule(chainRule.id);
      expect(payload).toEqual({ optimism: [ADDR_A] });
    });

    it('should return undefined when removing an unknown id', async () => {
      harness = createHarness({ source: {} });
      await flushPromises();
      expect(harness.state.removeRule('missing')).toBeUndefined();
    });
  });

  describe('no-op short-circuit', () => {
    it('should return undefined when the resulting payload matches the synced source', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();
      const chainRule = findRule(harness.state.rules.value, r => r.kind === 'chain');
      expect(harness.state.updateRule(chainRule.id, { chainId: 'eth', kind: 'chain' })).toBeUndefined();
    });
  });

  describe('source reactivity', () => {
    it('should re-sync rules when the source changes', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();
      expect(harness.state.rules.value.find(r => r.kind === 'chain')).toBeDefined();

      harness.source.value = { optimism: [ADDR_A] };
      await flushPromises();

      expect(harness.state.rules.value).toHaveLength(1);
      expect(harness.state.rules.value[0]).toMatchObject({
        address: ADDR_A,
        chainIds: ['optimism'],
        kind: 'address',
      });
    });
  });

  describe('buildPayload', () => {
    it('should round-trip the parsed payload', async () => {
      harness = createHarness({ source: { eth: [], optimism: [ADDR_A] } });
      await flushPromises();
      expect(harness.state.buildPayload()).toEqual({ eth: [], optimism: [ADDR_A] });
    });
  });
});
