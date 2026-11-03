import type { Component } from 'vue';
import { mountGeneric } from '@test/utils/mount-generic';
import { flushPromises } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import {
  BridgePotentialMatchesDialog,
  MatchAssetMovementsDialog,
  MatchBridgeTransactionsDialog,
  PotentialMatchesDialog,
} from '@/modules/history/events/dialog-components';
import { assetMovementMatchingKind } from '@/modules/history/events/matching/asset-movement-matching-kind';
import { bridgeMatchingKind } from '@/modules/history/events/matching/bridge-matching-kind';

const { matchingDialog, potentialDialog } = await vi.hoisted(async () => {
  const { defineComponent, h } = await import('vue');

  function stub(name: string): ReturnType<typeof defineComponent> {
    return defineComponent({
      name,
      props: { item: { default: undefined, type: null }, kind: { default: undefined, type: Object }, modelValue: Boolean },
      emits: ['update:modelValue', 'find-match'],
      setup: () => (): unknown => h('div'),
    });
  }

  return { matchingDialog: stub('UnmatchedMatchingDialog'), potentialDialog: stub('PotentialMatchesDialog') };
});

vi.mock('@/modules/history/events/UnmatchedMatchingDialog.vue', () => ({ default: matchingDialog }));
vi.mock('@/modules/history/events/PotentialMatchesDialog.vue', () => ({ default: potentialDialog }));

const item = { asset: 'ETH', events: [], groupIdentifier: 'group-a' };

describe.each<[string, Component, string, object]>([
  ['the movement matching dialog', MatchAssetMovementsDialog, 'UnmatchedMatchingDialog', assetMovementMatchingKind],
  ['the movement potential matches dialog', PotentialMatchesDialog, 'PotentialMatchesDialog', assetMovementMatchingKind],
  ['the bridge matching dialog', MatchBridgeTransactionsDialog, 'UnmatchedMatchingDialog', bridgeMatchingKind],
  ['the bridge potential matches dialog', BridgePotentialMatchesDialog, 'PotentialMatchesDialog', bridgeMatchingKind],
])('%s', (_, lazy, target, kind) => {
  const onFindMatch = vi.fn<(payload: unknown) => void>();

  async function mountLazy(): Promise<ReturnType<typeof mountGeneric>> {
    const host = mountGeneric(lazy, { item, modelValue: true, onFindMatch });
    await vi.waitFor(async () => {
      await flushPromises();
      expect(host.findComponent({ name: target }).exists()).toBe(true);
    });
    return host;
  }

  it('should load the dialog with its own kind bound', async () => {
    const host = await mountLazy();

    expect(toRaw(host.findComponent({ name: target }).props('kind'))).toBe(kind);
  });

  it('should pass the caller\'s props and listeners through to the dialog', async () => {
    const host = await mountLazy();
    const dialog = host.findComponent({ name: target });

    expect(dialog.props('item')).toStrictEqual(item);
    expect(dialog.props('modelValue')).toBe(true);
    dialog.vm.$emit('find-match', item);
    expect(onFindMatch).toHaveBeenCalledExactlyOnceWith(item);
  });
});
