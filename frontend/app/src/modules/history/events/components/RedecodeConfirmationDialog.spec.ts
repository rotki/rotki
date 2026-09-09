import type { Ref } from 'vue';
import type { PullEventPayload } from '@/modules/history/events/event-payloads';
import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import { HistoryEventEntryType } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import RedecodeConfirmationDialog from '@/modules/history/events/components/RedecodeConfirmationDialog.vue';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { createRuiPlugin } from '@/plugins/rui';

const { defaultEvmIndexerOrder, evmIndexersOrder } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    defaultEvmIndexerOrder: ref<string[]>([]),
    evmIndexersOrder: ref<Record<string, string[]>>({}),
  };
});

vi.mock('@/modules/settings/use-evm-indexer-settings', () => ({
  useEvmIndexerSettings: (): { defaultEvmIndexerOrder: Ref<string[]>; evmIndexersOrder: Ref<Record<string, string[]>> } => ({
    defaultEvmIndexerOrder,
    evmIndexersOrder,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): { getEvmChainName: (location: string) => string } => ({
    getEvmChainName: (location: string) => location,
  }),
}));

const evmEvent: PullEventPayload = {
  data: { location: 'optimism', txRef: '0xabc' },
  type: HistoryEventEntryType.EVM_EVENT,
};

const blockEvent: PullEventPayload = { data: [42], type: HistoryEventEntryType.ETH_BLOCK_EVENT };

/** `RuiDialog` teleports, so a pass-through keeps the card inside the wrapper. */
const DialogStub = { name: 'RuiDialog', props: ['modelValue', 'maxWidth'], template: '<div><slot /></div>' };

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<any> {
  return mount(RedecodeConfirmationDialog, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        PrioritizedList: {
          name: 'PrioritizedList',
          props: ['modelValue', 'allItems', 'itemDataName', 'disableDelete', 'dense', 'variant'],
          template: '<div />',
        },
        RuiDialog: DialogStub,
        SettingsItem: { name: 'SettingsItem', template: '<div><slot name="title" /><slot /></div>' },
      },
    },
    props: { payload: evmEvent, show: true, ...props },
  });
}

function order(wrapper: VueWrapper<any>): PrioritizedListId[] {
  return wrapper.findComponent({ name: 'PrioritizedList' }).props('modelValue');
}

interface ConfirmEvent { payload: PullEventPayload; deleteCustom: boolean; customIndexersOrder?: string[] }

async function proceed(wrapper: VueWrapper<any>): Promise<ConfirmEvent | undefined> {
  await wrapper.findComponent({ name: 'RuiButton' }).trigger('click');
  return wrapper.emitted<[ConfirmEvent]>('confirm')?.[0]?.[0];
}

describe('redecodeConfirmationDialog', () => {
  beforeEach(() => {
    set(defaultEvmIndexerOrder, []);
    set(evmIndexersOrder, {});
  });

  describe('the indexer order', () => {
    it('should open on the order stored for the event chain', () => {
      set(evmIndexersOrder, { optimism: [EvmIndexer.BLOCKSCOUT] });

      expect(order(createWrapper({ showIndexerOptions: true }))).toEqual([EvmIndexer.BLOCKSCOUT]);
    });

    it('should be offered only for an EVM event', () => {
      const wrapper = createWrapper({ payload: blockEvent, showIndexerOptions: true });

      expect(wrapper.findComponent({ name: 'PrioritizedList' }).exists()).toBe(false);
    });

    it('should be withheld when the caller did not ask for it', () => {
      const wrapper = createWrapper({ showIndexerOptions: false });

      expect(wrapper.findComponent({ name: 'PrioritizedList' }).exists()).toBe(false);
    });

    /** Removing the last indexer would leave the redecode nothing to ask. */
    it('should refuse to delete the only indexer left', () => {
      set(evmIndexersOrder, { optimism: [EvmIndexer.BLOCKSCOUT] });

      const list = createWrapper({ showIndexerOptions: true }).findComponent({ name: 'PrioritizedList' });

      expect(list.props('disableDelete')).toBe(true);
    });

    it('should allow deleting while more than one remains', () => {
      set(evmIndexersOrder, { optimism: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] });

      const list = createWrapper({ showIndexerOptions: true }).findComponent({ name: 'PrioritizedList' });

      expect(list.props('disableDelete')).toBe(false);
    });

    it('should warn when the stored order left no indexer at all', () => {
      set(evmIndexersOrder, { optimism: [] });

      const wrapper = createWrapper({ showIndexerOptions: true });

      expect(wrapper.text()).toContain('evm_settings.indexer.no_indexers_warning');
    });
  });

  describe('proceeding', () => {
    it('should hand back the payload it was given', async () => {
      expect((await proceed(createWrapper()))?.payload).toEqual(evmEvent);
    });

    it('should send the chosen indexer order for an EVM event', async () => {
      set(evmIndexersOrder, { optimism: [EvmIndexer.BLOCKSCOUT] });

      const event = await proceed(createWrapper({ showIndexerOptions: true }));

      expect(event?.customIndexersOrder).toEqual([EvmIndexer.BLOCKSCOUT]);
    });

    /** A non-EVM redecode has no indexer to pick, so the order is left out rather than sent empty. */
    it('should send no indexer order for a block event', async () => {
      set(defaultEvmIndexerOrder, [EvmIndexer.ETHERSCAN]);

      const event = await proceed(createWrapper({ payload: blockEvent }));

      expect(event?.customIndexersOrder).toBeUndefined();
    });

    it('should send no indexer order when none is left', async () => {
      set(evmIndexersOrder, { optimism: [] });

      const event = await proceed(createWrapper({ showIndexerOptions: true }));

      expect(event?.customIndexersOrder).toBeUndefined();
    });

    it('should close the dialog', async () => {
      const wrapper = createWrapper();

      await proceed(wrapper);

      expect(wrapper.emitted<[boolean]>('update:show')?.at(-1)?.[0]).toBe(false);
    });

    it('should stay silent when it was opened without a payload', async () => {
      const wrapper = createWrapper({ payload: undefined });

      await proceed(wrapper);

      expect(wrapper.emitted('confirm')).toBeUndefined();
      expect(wrapper.emitted<[boolean]>('update:show')?.at(-1)?.[0]).toBe(false);
    });
  });

  describe('custom events', () => {
    it('should warn that redecoding discards them', () => {
      expect(createWrapper({ hasCustomEvents: true }).text())
        .toContain('transactions.events.confirmation.reset.custom_events_warning');
    });

    it('should not warn when the group holds none', () => {
      expect(createWrapper().text())
        .not
        .toContain('transactions.events.confirmation.reset.custom_events_warning');
    });

    it('should tell the caller to delete them', async () => {
      expect((await proceed(createWrapper({ hasCustomEvents: true })))?.deleteCustom).toBe(true);
    });

    it('should leave them alone when the group holds none', async () => {
      expect((await proceed(createWrapper()))?.deleteCustom).toBe(false);
    });
  });

  /** The dialog is reused across groups, so what the previous one chose must not leak into the next. */
  it('should reseed the order each time it is reopened', async () => {
    set(evmIndexersOrder, { optimism: [EvmIndexer.BLOCKSCOUT] });
    const wrapper = createWrapper({ showIndexerOptions: true });

    set(evmIndexersOrder, { optimism: [EvmIndexer.ROUTESCAN] });
    await wrapper.setProps({ show: false });
    await wrapper.setProps({ show: true });

    expect(order(wrapper)).toEqual([EvmIndexer.ROUTESCAN]);
  });
});
