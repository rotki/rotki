import type { SupportedAsset } from '@rotki/common';
import type { AssetUpdateConflictResult } from '@/modules/assets/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AssetConflictDialog from '@/modules/shell/app/AssetConflictDialog.vue';

/**
 * `BigDialog` teleports and owns the footer buttons, so a pass-through stands in for it: the slots
 * render inline, and the two buttons stand for confirming and dismissing.
 */
const BigDialogStub = {
  emits: ['confirm', 'cancel'],
  name: 'BigDialog',
  props: ['title', 'subtitle', 'display', 'action', 'layout', 'persistent'],
  template: `<div>
    <slot name="subtitle" />
    <slot />
    <slot name="left-buttons" />
    <button data-testid="stub-confirm" @click="$emit('confirm')" />
    <button data-testid="stub-cancel" @click="$emit('cancel')" />
  </div>`,
};

function conflict(identifier: string): AssetUpdateConflictResult {
  const asset: SupportedAsset = { identifier, isRebasing: false, name: identifier };
  return { identifier, local: asset, remote: { ...asset, name: `${identifier} remote` } };
}

function createWrapper(conflicts: AssetUpdateConflictResult[]): VueWrapper<InstanceType<typeof AssetConflictDialog>> {
  return mount(AssetConflictDialog, {
    global: {
      stubs: {
        AssetConflictRow: true,
        BigDialog: BigDialogStub,
        // Globally stubbed to `true`, which would swallow the identifiers the warning names.
        I18nT: { template: '<span><slot name="identifiers" /></span>' },
        RuiDataTable: true,
      },
    },
    props: {
      conflicts,
    },
  });
}

describe('assetConflictDialog', () => {
  describe('confirming', () => {
    it('should keep the remote asset for every conflict by default', async () => {
      const wrapper = createWrapper([conflict('eth'), conflict('btc')]);

      await wrapper.find('[data-testid=stub-confirm]').trigger('click');

      expect(wrapper.emitted('resolve')?.[0]?.[0]).toEqual({ btc: 'remote', eth: 'remote' });
    });

    it('should let the dialog be confirmed once every conflict has a strategy', async () => {
      const wrapper = createWrapper([conflict('eth')]);
      await nextTick();

      expect(wrapper.findComponent(BigDialogStub).props('action')).toMatchObject({ disabled: false });
    });
  });

  /**
   * Dismissing the two bulk choices is not abandoning the update: the user is choosing to keep
   * what they have, so the dialog resolves as local rather than emitting a cancel that would
   * leave the conflicts unanswered.
   */
  describe('dismissing', () => {
    it('should keep the local asset when the bulk choices are dismissed', async () => {
      const wrapper = createWrapper([conflict('eth'), conflict('btc')]);

      await wrapper.find('[data-testid=stub-cancel]').trigger('click');

      expect(wrapper.emitted('resolve')?.[0]?.[0]).toEqual({ btc: 'local', eth: 'local' });
      expect(wrapper.emitted('cancel')).toBeUndefined();
    });

    it('should abandon the update when dismissed while resolving by hand', async () => {
      const wrapper = createWrapper([conflict('eth')]);

      await wrapper.find('[data-testid=manage-conflicts]').trigger('click');
      await wrapper.find('[data-testid=stub-cancel]').trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
      expect(wrapper.emitted('resolve')).toBeUndefined();
    });
  });

  describe('resolving by hand', () => {
    it('should offer the table only after the user asks to manage the conflicts', async () => {
      const wrapper = createWrapper([conflict('eth')]);

      expect(wrapper.findComponent({ name: 'RuiDataTable' }).exists()).toBe(false);

      await wrapper.find('[data-testid=manage-conflicts]').trigger('click');

      expect(wrapper.findComponent({ name: 'RuiDataTable' }).exists()).toBe(true);
    });

    it('should stop offering the bulk choices once the table is showing', async () => {
      const wrapper = createWrapper([conflict('eth')]);

      await wrapper.find('[data-testid=manage-conflicts]').trigger('click');

      expect(wrapper.find('[data-testid=manage-conflicts]').exists()).toBe(false);
      expect(wrapper.findComponent(BigDialogStub).props('action')).toMatchObject({
        primary: undefined,
        secondary: undefined,
      });
    });
  });

  describe('the duplicate warning', () => {
    it('should name an identifier the update sent twice', () => {
      const wrapper = createWrapper([conflict('eth'), conflict('eth'), conflict('btc')]);

      const alert = wrapper.find('[data-testid=alert]');

      expect(alert.exists()).toBe(true);
      expect(alert.text()).toContain('eth');
      expect(alert.text()).not.toContain('btc');
    });

    it('should not warn when every identifier is distinct', () => {
      const wrapper = createWrapper([conflict('eth'), conflict('btc')]);

      expect(wrapper.find('[data-testid=alert]').exists()).toBe(false);
    });
  });
});
