import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { effectScope, ref, type Ref } from 'vue';
import {
  type DisabledChainQueries,
  useDisabledChainQueriesState,
  type UseDisabledChainQueriesStateReturn,
} from '@/modules/settings/general/use-disabled-chain-queries-state';

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

describe('useDisabledChainQueriesState', () => {
  let harness: Harness;

  afterEach(() => {
    harness?.dispose();
  });

  describe('initial sync', () => {
    it('should not touch local state until ready', async () => {
      harness = createHarness({ ready: false, source: { eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] } });
      const { state } = harness;

      await flushPromises();

      expect(state.visibleChainIds.value).toEqual([]);
      expect(state.excludedAddresses.value).toEqual({});
    });

    it('should sync when ready flips true', async () => {
      harness = createHarness({ ready: false, source: { eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] } });
      const { ready, state } = harness;

      ready.value = true;
      await flushPromises();

      expect(state.visibleChainIds.value).toEqual(['eth']);
      expect(state.excludedAddresses.value).toEqual({
        eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
      });
    });

    it('should sync immediately when mounted with ready already true', async () => {
      harness = createHarness({ ready: true, source: { eth: [], optimism: ['0xc37b40ABdB939635068d3c5f13E7faF686F03B65'] } });
      const { state } = harness;
      await flushPromises();

      expect(state.visibleChainIds.value).toEqual(['eth', 'optimism']);
      expect(state.excludedAddresses.value).toEqual({
        eth: [],
        optimism: ['0xc37b40ABdB939635068d3c5f13E7faF686F03B65'],
      });
    });

    it('should skip unsupported chains during sync', async () => {
      harness = createHarness({ source: { not_a_real_chain: [] } });
      await flushPromises();
      expect(harness.state.visibleChainIds.value).toEqual([]);
    });
  });

  describe('toggle semantics', () => {
    beforeEach(async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();
    });

    it('should treat a chain with an empty list as entirely disabled', () => {
      expect(harness.state.isEntireChainDisabled('eth')).toBe(true);
      expect(harness.state.isTransientlyDisabled('eth')).toBe(false);
    });

    it('should reveal the picker without producing a commit on toggle OFF', () => {
      const payload = harness.state.setEntireChainDisabled('eth', false);
      expect(payload).toBeUndefined();
      expect(harness.state.isEntireChainDisabled('eth')).toBe(false);
      expect(harness.state.isTransientlyDisabled('eth')).toBe(true);
    });

    it('should clear addresses and commit { chain: [] } on toggle ON', async () => {
      harness.source.value = { optimism: ['0xc37b40ABdB939635068d3c5f13E7faF686F03B65'] };
      await flushPromises();

      const payload = harness.state.setEntireChainDisabled('optimism', true);
      expect(payload).toEqual({ optimism: [] });
      expect(harness.state.isEntireChainDisabled('optimism')).toBe(true);
    });

    it('should clear the transient flag once an address is added', () => {
      harness.state.setEntireChainDisabled('eth', false);
      const payload = harness.state.setExcludedAddresses('eth', ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c']);
      expect(payload).toEqual({ eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] });
      expect(harness.state.isTransientlyDisabled('eth')).toBe(false);
      expect(harness.state.isEntireChainDisabled('eth')).toBe(false);
    });
  });

  describe('chain selection', () => {
    beforeEach(async () => {
      harness = createHarness({ source: {} });
      await flushPromises();
    });

    it('should commit an empty list for newly added chains', () => {
      const payload = harness.state.selectChains(['eth']);
      expect(payload).toEqual({ eth: [] });
    });

    it('should drop deselected chains from the payload and from the revealed set', () => {
      harness.state.selectChains(['eth', 'optimism']);
      harness.state.setEntireChainDisabled('optimism', false);
      expect(harness.state.isTransientlyDisabled('optimism')).toBe(true);

      const payload = harness.state.selectChains(['eth']);
      expect(payload).toEqual({ eth: [] });
      expect(harness.state.visibleChainIds.value).toEqual(['eth']);
      expect(harness.state.isTransientlyDisabled('optimism')).toBe(false);
    });
  });

  describe('refresh persistence', () => {
    it('should restore an empty-list chain as "entire chain disabled" after a remount', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();
      harness.state.setEntireChainDisabled('eth', false);
      expect(harness.state.isTransientlyDisabled('eth')).toBe(true);

      // Simulate a browser refresh: dispose this scope, build a fresh one with the same source.
      harness.dispose();
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();

      expect(harness.state.visibleChainIds.value).toEqual(['eth']);
      expect(harness.state.isEntireChainDisabled('eth')).toBe(true);
      expect(harness.state.isTransientlyDisabled('eth')).toBe(false);
    });

    it('should preserve excluded addresses across a remount', async () => {
      harness = createHarness({ source: { optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] } });
      await flushPromises();

      expect(harness.state.visibleChainIds.value).toEqual(['optimism']);
      expect(harness.state.excludedAddresses.value).toEqual({
        optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
      });
    });
  });

  describe('source reactivity', () => {
    it('should re-sync local state when the source changes', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();
      expect(harness.state.visibleChainIds.value).toEqual(['eth']);

      harness.source.value = { optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] };
      await flushPromises();

      expect(harness.state.visibleChainIds.value).toEqual(['optimism']);
      expect(harness.state.excludedAddresses.value).toEqual({
        optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
      });
    });

    it('should keep the picker revealed for a chain after a store round-trip', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();
      harness.state.setEntireChainDisabled('eth', false);
      expect(harness.state.isTransientlyDisabled('eth')).toBe(true);

      // Backend echoes the still-empty payload back.
      harness.source.value = { eth: [] };
      await flushPromises();

      expect(harness.state.isTransientlyDisabled('eth')).toBe(true);
    });
  });

  describe('no-op short-circuit', () => {
    it('should return undefined from selectChains when the selection matches the synced source', async () => {
      harness = createHarness({ source: { eth: [], optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] } });
      await flushPromises();

      expect(harness.state.selectChains(['eth', 'optimism'])).toBeUndefined();
    });

    it('should return undefined from setExcludedAddresses when the addresses match the synced source', async () => {
      harness = createHarness({ source: { optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] } });
      await flushPromises();

      expect(
        harness.state.setExcludedAddresses('optimism', ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c']),
      ).toBeUndefined();
    });

    it('should return undefined from setEntireChainDisabled(true) when the chain is already empty', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();

      expect(harness.state.setEntireChainDisabled('eth', true)).toBeUndefined();
    });

    it('should not re-commit after a remount with the same source', async () => {
      harness = createHarness({ source: { eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] } });
      await flushPromises();

      // Same payload as what was already synced — no commit needed.
      expect(
        harness.state.setExcludedAddresses('eth', ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c']),
      ).toBeUndefined();
    });

    it('should still commit a genuine change after a no-op call', async () => {
      harness = createHarness({ source: { eth: [] } });
      await flushPromises();

      expect(harness.state.setEntireChainDisabled('eth', true)).toBeUndefined();

      const payload = harness.state.setExcludedAddresses(
        'eth',
        ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
      );
      expect(payload).toEqual({ eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] });
    });
  });

  describe('buildPayload', () => {
    it('should round-trip the visible chain set verbatim', async () => {
      harness = createHarness({ source: { eth: [], optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'] } });
      await flushPromises();

      expect(harness.state.buildPayload()).toEqual({
        eth: [],
        optimism: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'],
      });
    });
  });
});
