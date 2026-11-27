import type { DataMigrationStatusData, DbUpgradeStatusData } from '@/modules/core/messaging/types';
import { I18nTStub } from '@test/stubs/I18nT';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { type Pinia, setActivePinia, storeToRefs } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { UpgradeRowStatus } from '@/modules/auth/upgrade/upgrade-progress';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import UpgradeProgressDisplay from './UpgradeProgressDisplay.vue';

const START = new Date('2026-11-27T12:00:00Z');

/** A v51 to v54 upgrade on v53, five steps into twelve. */
function upgrade(overrides: Partial<DbUpgradeStatusData['currentUpgrade']> = {}): DbUpgradeStatusData {
  return {
    currentUpgrade: { currentStep: 5, description: 'Migrating history events', toVersion: 53, totalSteps: 12, ...overrides },
    startVersion: 52,
    targetVersion: 54,
  };
}

function migration(): DataMigrationStatusData {
  return {
    currentMigration: { currentStep: 1, description: null, totalSteps: 3, version: 18 },
    startVersion: 18,
    targetVersion: 19,
  };
}

function text(wrapper: VueWrapper, testId: string): string {
  return wrapper.find(`[data-testid=${testId}]`).text();
}

describe('modules/auth/upgrade/UpgradeProgressDisplay', () => {
  let pinia: Pinia;

  function mountDisplay(completed: boolean = false): VueWrapper<InstanceType<typeof UpgradeProgressDisplay>> {
    return mount(UpgradeProgressDisplay, {
      global: { plugins: [pinia], stubs: { I18nT: I18nTStub } },
      props: { completed },
    });
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(START);
    pinia = createCustomPinia();
    setActivePinia(pinia);
    const store = useSessionAuthStore();
    store.setUnlockingProfile('alice');
    set(storeToRefs(useMainStore()).dataDirectory, '/data');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should show the version and step of a running upgrade with the profile it belongs to', () => {
    useSessionAuthStore().updateDbUpgradeStatus(upgrade());
    const wrapper = mountDisplay();

    expect(text(wrapper, 'db-upgrade-title')).toBe('login.db_upgrade.title.running');
    expect(text(wrapper, 'db-upgrade-subtitle')).toContain('alice');
    expect(text(wrapper, 'db-upgrade-subtitle')).toContain('login.db_upgrade.range.version::51, 54');
    expect(text(wrapper, 'db-upgrade-summary'))
      .toBe('login.db_upgrade.progress.version::3, 2 · login.db_upgrade.progress.step::5, 12');
    expect(text(wrapper, 'db-upgrade-description')).toBe('Migrating history events');
    expect(wrapper.find('[data-testid=db-upgrade-reassurance]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=db-upgrade-failure]').exists()).toBe(false);
  });

  it('should list each version of the run as done, current or pending', () => {
    useSessionAuthStore().updateDbUpgradeStatus(upgrade());
    const wrapper = mountDisplay();

    const statuses = wrapper.findAll('[data-testid=db-upgrade-version]').map(row => row.attributes('data-status'));
    expect(statuses).toEqual([UpgradeRowStatus.DONE, UpgradeRowStatus.CURRENT, UpgradeRowStatus.PENDING]);
  });

  it('should say it is preparing until the first version reports its steps', () => {
    useSessionAuthStore().updateDbUpgradeStatus(upgrade({ currentStep: 0, toVersion: 52, totalSteps: 0 }));
    const wrapper = mountDisplay();

    expect(text(wrapper, 'db-upgrade-summary')).toBe('login.db_upgrade.progress.preparing');
  });

  it('should tick the elapsed time from the first upgrade message', async () => {
    useSessionAuthStore().updateDbUpgradeStatus(upgrade());
    const wrapper = mountDisplay();

    expect(text(wrapper, 'db-upgrade-elapsed')).toContain('0s');

    await vi.advanceTimersByTimeAsync(65_000);

    expect(text(wrapper, 'db-upgrade-elapsed')).toContain('1m 05s');
  });

  it('should time each version from when it was first reported', async () => {
    const store = useSessionAuthStore();
    store.updateDbUpgradeStatus(upgrade({ toVersion: 52 }));
    vi.advanceTimersByTime(7_000);
    store.updateDbUpgradeStatus(upgrade({ toVersion: 53 }));
    const wrapper = mountDisplay();

    await vi.advanceTimersByTimeAsync(3_000);

    const rows = wrapper.findAll('[data-testid=db-upgrade-version]');
    expect(rows[0].text()).toContain('7s');
    expect(rows[1].text()).toContain('5/12');
  });

  it('should hand off with the version reached and freeze the time it took', async () => {
    const store = useSessionAuthStore();
    store.updateDbUpgradeStatus(upgrade({ currentStep: 17, toVersion: 54, totalSteps: 17 }));
    vi.advanceTimersByTime(4_000);
    const wrapper = mountDisplay(true);

    expect(wrapper.find('[data-testid=db-upgrade]').attributes('data-outcome')).toBe('done');
    expect(text(wrapper, 'db-upgrade-title')).toBe('login.db_upgrade.title.done::54');
    expect(text(wrapper, 'db-upgrade-summary')).toBe('login.db_upgrade.done.opening');
    expect(text(wrapper, 'db-upgrade-description')).toBe('login.db_upgrade.done.took::4s');
    expect(wrapper.findAll('[data-testid=db-upgrade-version]').every(row => row.attributes('data-status') === UpgradeRowStatus.DONE)).toBe(true);
    expect(wrapper.find('[data-testid=db-upgrade-reassurance]').exists()).toBe(false);

    await vi.advanceTimersByTimeAsync(10_000);

    expect(text(wrapper, 'db-upgrade-description')).toBe('login.db_upgrade.done.took::4s');
  });

  it('should report the restored backup and where it is when the backend upgrade fails', async () => {
    const store = useSessionAuthStore();
    store.updateDbUpgradeStatus(upgrade({ toVersion: 54 }));
    store.failUpgrade('Failed at database upgrade from version 53 to 54: no such column');
    const wrapper = mountDisplay();

    expect(text(wrapper, 'db-upgrade-title')).toBe('login.db_upgrade.title.failed');
    expect(text(wrapper, 'db-upgrade-error')).toBe('Failed at database upgrade from version 53 to 54: no such column');
    expect(text(wrapper, 'db-upgrade-restored')).toBe('login.db_upgrade.failed.restored::53, 54');
    expect(text(wrapper, 'db-upgrade-backup-path')).toBe('/data/users/alice');
    expect(wrapper.find('[data-testid=db-upgrade-version][data-status=current]').text()).toContain('login.db_upgrade.rows.version::54');
    expect(wrapper.find('[data-testid=db-upgrade-reassurance]').exists()).toBe(false);

    await wrapper.find('[data-testid=db-upgrade-back]').trigger('click');

    expect(wrapper.emitted('back')).toHaveLength(1);
  });

  it('should not claim a restore when the unlock failed for another reason', () => {
    const store = useSessionAuthStore();
    store.updateDbUpgradeStatus(upgrade());
    store.failUpgrade('Request timed out after 30000ms');
    const wrapper = mountDisplay();

    expect(wrapper.find('[data-testid=db-upgrade-restored]').exists()).toBe(false);
    expect(wrapper.text()).toContain('login.db_upgrade.failed.backups_kept');
    expect(text(wrapper, 'db-upgrade-backup-path')).toBe('/data/users/alice');
  });

  it('should offer no folder buttons outside the desktop app', () => {
    const store = useSessionAuthStore();
    store.updateDbUpgradeStatus(upgrade());
    store.failUpgrade('boom');
    const wrapper = mountDisplay();

    expect(wrapper.find('[data-testid=db-upgrade-open-logs]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=db-upgrade-open-backups]').exists()).toBe(false);
    expect(wrapper.text()).toContain('login.db_upgrade.failed.logs_web');
  });

  it('should show a running data migration in its own words', () => {
    useSessionAuthStore().updateDataMigrationStatus(migration());
    const wrapper = mountDisplay();

    expect(text(wrapper, 'db-upgrade-title')).toBe('login.db_upgrade.title.migrating');
    expect(text(wrapper, 'db-upgrade-summary'))
      .toBe('login.db_upgrade.progress.migration::2, 1 · login.db_upgrade.progress.step::1, 3');
    expect(wrapper.text()).toContain('login.db_upgrade.reassurance.migration');
    expect(wrapper.text()).not.toContain('login.db_upgrade.reassurance.keep_open');
  });

  it('should report the DB upgrade, not the migrations after it, once the unlock finishes', async () => {
    const store = useSessionAuthStore();
    store.updateDbUpgradeStatus(upgrade({ currentStep: 17, toVersion: 54, totalSteps: 17 }));
    store.updateDataMigrationStatus(migration());
    const wrapper = mountDisplay();

    expect(text(wrapper, 'db-upgrade-title')).toBe('login.db_upgrade.title.migrating');

    await wrapper.setProps({ completed: true });
    await nextTick();

    expect(text(wrapper, 'db-upgrade-title')).toBe('login.db_upgrade.title.done::54');
  });

  it('should render nothing without an upgrade or migration', () => {
    const wrapper = mountDisplay();

    expect(wrapper.find('[data-testid=db-upgrade]').exists()).toBe(false);
  });
});
