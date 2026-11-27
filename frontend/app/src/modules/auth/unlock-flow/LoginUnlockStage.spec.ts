import { createCustomPinia } from '@test/utils/create-pinia';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { type Pinia, setActivePinia, storeToRefs } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import AssetConflictStage from '@/modules/auth/unlock-flow/AssetConflictStage.vue';
import AssetUpdateProgress from '@/modules/auth/unlock-flow/AssetUpdateProgress.vue';
import AssetUpdatePrompt from '@/modules/auth/unlock-flow/AssetUpdatePrompt.vue';
import { UnlockErrorKind, UnlockPhase, type UnlockState } from '@/modules/auth/unlock-flow/use-unlock-flow';
import UpgradeProgressDisplay from '@/modules/auth/upgrade/UpgradeProgressDisplay.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import LoginUnlockStage from './LoginUnlockStage.vue';

const CHANGES = { changes: 5, local: 37, remote: 42, upToVersion: 42 };

const UPGRADE = { currentUpgrade: { currentStep: 1, description: '', totalSteps: 2, toVersion: 2 }, startVersion: 1, targetVersion: 2 };

function mountStage(
  state: UnlockState,
  pinia: Pinia,
  updateAccepted = false,
): VueWrapper<InstanceType<typeof LoginUnlockStage>> {
  return shallowMount(LoginUnlockStage, { global: { plugins: [pinia] }, props: { state, updateAccepted } });
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
    const prompt = wrapper.findComponent(AssetUpdatePrompt);

    expect(prompt.props('versions')).toStrictEqual(CHANGES);
    prompt.vm.$emit('confirm', { always: false, upToVersion: 40 });
    await nextTick();

    expect(wrapper.emitted('confirm')).toEqual([[40]]);
  });

  it('should remember the choice to apply later updates automatically', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);

    wrapper.findComponent(AssetUpdatePrompt).vm.$emit('confirm', { always: true, upToVersion: 42 });
    await nextTick();

    expect(localStorage.getItem('rotki.asset_update.auto_apply')).toBe('true');
    expect(wrapper.emitted('confirm')).toEqual([[42]]);
  });

  it('should show the versions of an update applied without a prompt', () => {
    const wrapper = mountStage({ automatic: true, changes: CHANGES, kind: UnlockPhase.applyingUpdate }, pinia, true);

    expect(wrapper.findComponent(AssetUpdateProgress).props()).toMatchObject({ automatic: true, from: 37, to: 42 });
  });

  it('should record the skipped version and emit skip when asked not to be reminded', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);

    wrapper.findComponent(AssetUpdatePrompt).vm.$emit('skip', true);
    await nextTick();

    expect(localStorage.getItem('rotki_skip_asset_db_version')).toBe('42');
    expect(wrapper.emitted('skip')).toHaveLength(1);
  });

  it('should emit skip without recording a version on a plain skip', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);

    wrapper.findComponent(AssetUpdatePrompt).vm.$emit('skip', false);
    await nextTick();

    // stays at the default (0): the remote version (42) is not recorded
    expect(localStorage.getItem('rotki_skip_asset_db_version')).toBe('0');
    expect(wrapper.emitted('skip')).toHaveLength(1);
  });

  it('should show the conflicts with the confirmed version and forward resolve and skip', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);
    wrapper.findComponent(AssetUpdatePrompt).vm.$emit('confirm', { always: false, upToVersion: 40 });
    await wrapper.setProps({ state: { conflicts: [], kind: UnlockPhase.conflicts } });
    const stage = wrapper.findComponent(AssetConflictStage);

    expect(stage.props('version')).toBe(40);
    stage.vm.$emit('resolve', { foo: 'remote' });
    stage.vm.$emit('skip');
    await nextTick();

    expect(wrapper.emitted('resolve')).toEqual([[{ foo: 'remote' }]]);
    expect(wrapper.emitted('skip')).toHaveLength(1);
  });

  it('should follow an accepted update from the prompt through its restart', async () => {
    const wrapper = mountStage({ changes: CHANGES, kind: UnlockPhase.updatePrompt }, pinia);
    wrapper.findComponent(AssetUpdatePrompt).vm.$emit('confirm', { always: false, upToVersion: 42 });
    await wrapper.setProps({ state: { kind: UnlockPhase.restarting }, updateAccepted: true });
    const progress = wrapper.findComponent(AssetUpdateProgress);

    expect(progress.props()).toMatchObject({ from: 37, phase: UnlockPhase.restarting, to: 42 });
  });

  it('should word a failed restart and pass the back request on', async () => {
    const wrapper = mountStage({ error: { kind: UnlockErrorKind.restartFailed }, kind: UnlockPhase.error }, pinia, true);
    const progress = wrapper.findComponent(AssetUpdateProgress);

    expect(progress.props('errorKind')).toBe(UnlockErrorKind.restartFailed);
    expect(progress.props('error')).toBe('unlock_flow.errors.restart_failed');
    progress.vm.$emit('back');
    await nextTick();

    expect(wrapper.emitted('leave-update')).toHaveLength(1);
  });

  it('should pass a failed update\'s own message on', () => {
    const wrapper = mountStage({ error: { kind: UnlockErrorKind.updateFailed, message: 'no space' }, kind: UnlockPhase.error }, pinia, true);

    expect(wrapper.findComponent(AssetUpdateProgress).props('error')).toBe('no space');
  });

  it('should leave the in-flight phases of a plain login to the form', () => {
    const wrapper = mountStage({ kind: UnlockPhase.authenticating }, pinia);

    expect(wrapper.findComponent(AssetUpdateProgress).exists()).toBe(false);
    expect(wrapper.findComponent(UpgradeProgressDisplay).exists()).toBe(false);
  });

  it('should show the upgrade progress while unlocking when an upgrade is visible', () => {
    set(storeToRefs(useSessionAuthStore()).dbUpgradeStatus, UPGRADE);
    const wrapper = mountStage({ kind: UnlockPhase.unlocking }, pinia);
    expect(wrapper.findComponent(UpgradeProgressDisplay).exists()).toBe(true);
  });

  it('should prefer the upgrade progress over the asset update when the unlock after it upgrades', () => {
    set(storeToRefs(useSessionAuthStore()).dbUpgradeStatus, UPGRADE);
    const wrapper = mountStage({ kind: UnlockPhase.unlocking }, pinia, true);

    expect(wrapper.findComponent(UpgradeProgressDisplay).exists()).toBe(true);
    expect(wrapper.findComponent(AssetUpdateProgress).exists()).toBe(false);
  });

  it('should keep the finished upgrade on screen while the session loads', () => {
    set(storeToRefs(useSessionAuthStore()).dbUpgradeStatus, { ...UPGRADE, currentUpgrade: { ...UPGRADE.currentUpgrade, currentStep: 2 } });
    const wrapper = mountStage({ kind: UnlockPhase.loadingSession }, pinia);
    const display = wrapper.findComponent(UpgradeProgressDisplay);

    expect(display.exists()).toBe(true);
    expect(display.props('completed')).toBe(true);
  });

  it('should show a failed upgrade in the error phase and pass its back request on', async () => {
    const store = useSessionAuthStore();
    store.updateDbUpgradeStatus(UPGRADE);
    store.failUpgrade('Failed at database upgrade from version 1 to 2: boom');
    const wrapper = mountStage({ error: { kind: UnlockErrorKind.unknown, message: 'boom' }, kind: UnlockPhase.error }, pinia);
    const display = wrapper.findComponent(UpgradeProgressDisplay);

    expect(display.exists()).toBe(true);
    display.vm.$emit('back');
    await nextTick();

    expect(wrapper.emitted('leave-upgrade')).toHaveLength(1);
  });

  it('should leave an error without an upgrade failure to the login form', () => {
    set(storeToRefs(useSessionAuthStore()).dbUpgradeStatus, UPGRADE);
    const wrapper = mountStage({ error: { kind: UnlockErrorKind.wrongPassword }, kind: UnlockPhase.error }, pinia);

    expect(wrapper.findComponent(UpgradeProgressDisplay).exists()).toBe(false);
  });
});
