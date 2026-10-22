import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';
import RestoreOutcomeNotice from '@/modules/auth/login/RestoreOutcomeNotice.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { RestoreOutcomeKind, useRestoreOutcomeNotice } from '@/modules/session/use-restore-outcome-notice';

/** The installed `RuiAlert` does not resolve to a component here, and the seam is its type and `@close`. */
const AlertStub = defineComponent({
  emits: ['close'],
  name: 'AlertStub',
  props: { title: { default: '', type: String }, type: { default: '', type: String } },
  template: '<div :data-type="type">{{ title }} <slot /></div>',
});

function createWrapper(): VueWrapper<InstanceType<typeof RestoreOutcomeNotice>> {
  return mount(RestoreOutcomeNotice, {
    global: { stubs: { RuiAlert: AlertStub } },
  });
}

describe('restoreOutcomeNotice', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    set(storeToRefs(useSessionAuthStore()).logged, false);
    useRestoreOutcomeNotice().dismiss();
  });

  it('should say which backup was restored after a restore logged out', () => {
    useRestoreOutcomeNotice().show({ kind: RestoreOutcomeKind.RESTORED, message: 'Restored the backup of 19 Oct' });

    const notice = createWrapper().find('[data-testid=restore-outcome-notice]');

    expect(notice.attributes('data-type')).toBe('success');
    expect(notice.text()).toContain('Restored the backup of 19 Oct');
  });

  it('should say why a restore failed', () => {
    useRestoreOutcomeNotice().show({ kind: RestoreOutcomeKind.FAILED, message: 'The backup is newer' });

    const notice = createWrapper().find('[data-testid=restore-outcome-notice]');

    expect(notice.attributes('data-type')).toBe('error');
    expect(notice.text()).toContain('The backup is newer');
  });

  it('should show nothing after any other logout', () => {
    expect(createWrapper().find('[data-testid=restore-outcome-notice]').exists()).toBe(false);
  });

  it('should go away when closed', async () => {
    useRestoreOutcomeNotice().show({ kind: RestoreOutcomeKind.RESTORED, message: 'Restored' });
    const wrapper = createWrapper();

    wrapper.findComponent(AlertStub).vm.$emit('close');
    await nextTick();

    expect(get(useRestoreOutcomeNotice().outcome)).toBeUndefined();
    expect(wrapper.find('[data-testid=restore-outcome-notice]').exists()).toBe(false);
  });

  it('should go away once the user is logged in again', async () => {
    useRestoreOutcomeNotice().show({ kind: RestoreOutcomeKind.RESTORED, message: 'Restored' });

    set(storeToRefs(useSessionAuthStore()).logged, true);
    await nextTick();

    expect(get(useRestoreOutcomeNotice().outcome)).toBeUndefined();
  });
});
