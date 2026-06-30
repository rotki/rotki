import type { Pinia } from 'pinia';
import { createCustomPinia } from '@test/utils/create-pinia';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import { UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import UpgradeProgressDisplay from '@/modules/auth/upgrade/UpgradeProgressDisplay.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import AssetConflictDialog from '@/modules/shell/app/AssetConflictDialog.vue';
import AssetUpdateMessage from '@/modules/shell/app/AssetUpdateMessage.vue';
import AssetUpdateStatus from '@/modules/shell/app/AssetUpdateStatus.vue';
import LoginUnlockStage from './LoginUnlockStage.vue';

const CHANGES = { changes: 5, local: 37, remote: 42, upToVersion: 42 };

function mountStage(state: UnlockState, pinia: Pinia): VueWrapper<InstanceType<typeof LoginUnlockStage>> {
  return shallowMount(LoginUnlockStage, { global: { plugins: [pinia] }, props: { state } });
}

describe('modules/auth/unlock-flow/LoginUnlockStage', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    localStorage.clear();
  });

  it('should render the update prompt and emit confirm with the chosen version', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);
    const message = wrapper.findComponent(AssetUpdateMessage);

    expect(message.exists()).toBe(true);
    message.vm.$emit('confirm');
    await nextTick();

    expect(wrapper.emitted('confirm')).toEqual([[42]]);
  });

  it('should record the skipped version and emit skip on a permanent dismiss', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);

    wrapper.findComponent(AssetUpdateMessage).vm.$emit('dismiss', true);
    await nextTick();

    expect(localStorage.getItem('rotki_skip_asset_db_version')).toBe('42');
    expect(wrapper.emitted('skip')).toHaveLength(1);
  });

  it('should emit skip without recording a version on a plain dismiss', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);

    wrapper.findComponent(AssetUpdateMessage).vm.$emit('dismiss', false);
    await nextTick();

    // stays at the default (0) — the remote version (42) is not recorded
    expect(localStorage.getItem('rotki_skip_asset_db_version')).toBe('0');
    expect(wrapper.emitted('skip')).toHaveLength(1);
  });

  it('should render the conflict dialog and forward resolve/cancel', async () => {
    const wrapper = mountStage({ conflicts: [], kind: UnlockPhase.conflicts }, pinia);
    const dialog = wrapper.findComponent(AssetConflictDialog);

    expect(dialog.exists()).toBe(true);
    dialog.vm.$emit('resolve', { foo: 'remote' });
    dialog.vm.$emit('cancel');
    await nextTick();

    expect(wrapper.emitted('resolve')).toEqual([[{ foo: 'remote' }]]);
    expect(wrapper.emitted('skip')).toHaveLength(1);
  });

  it('should render the applying status while an update is in flight', () => {
    const wrapper = mountStage({ kind: UnlockPhase.applyingUpdate }, pinia);
    expect(wrapper.findComponent(AssetUpdateStatus).props('status')).toBe('applying');
  });

  it('should render the checking status while looking for an update', () => {
    const wrapper = mountStage({ kind: UnlockPhase.checkingUpdate }, pinia);
    expect(wrapper.findComponent(AssetUpdateStatus).props('status')).toBe('checking');
  });

  it('should label the spinner while restarting the backend', () => {
    const wrapper = mountStage({ kind: UnlockPhase.restarting }, pinia);
    expect(wrapper.findComponent(AssetUpdateStatus).exists()).toBe(false);
    expect(wrapper.find('p').exists()).toBe(true);
  });

  it('should show the upgrade progress while unlocking when an upgrade is visible', () => {
    set(storeToRefs(useSessionAuthStore()).dbUpgradeStatus, { currentUpgrade: { currentStep: 1, description: '', totalSteps: 2, toVersion: 2 }, startVersion: 1, targetVersion: 2 });
    const wrapper = mountStage({ kind: UnlockPhase.unlocking }, pinia);
    expect(wrapper.findComponent(UpgradeProgressDisplay).exists()).toBe(true);
  });

  it('should fall back to a spinner for plain in-flight phases', () => {
    const wrapper = mountStage({ kind: UnlockPhase.authenticating }, pinia);
    expect(wrapper.findComponent(AssetUpdateMessage).exists()).toBe(false);
    expect(wrapper.findComponent(UpgradeProgressDisplay).exists()).toBe(false);
    expect(wrapper.find('.flex.justify-center').exists()).toBe(true);
  });
});
