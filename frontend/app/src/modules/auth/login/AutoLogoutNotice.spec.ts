import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAutoLogoutNotice } from '@/modules/auth/auto-logout/use-auto-logout-notice';
import AutoLogoutNotice from '@/modules/auth/login/AutoLogoutNotice.vue';

/** The installed `RuiAlert` does not resolve to a component here, and the seam is the `@close` binding. */
const AlertStub = defineComponent({
  emits: ['close'],
  name: 'AlertStub',
  template: '<div><slot /></div>',
});

function createWrapper(): VueWrapper<InstanceType<typeof AutoLogoutNotice>> {
  return mount(AutoLogoutNotice, {
    global: { stubs: { RuiAlert: AlertStub } },
  });
}

describe('autoLogoutNotice', () => {
  beforeEach(() => {
    useAutoLogoutNotice().dismiss();
  });

  it('should say how long the session was idle after an idle logout', () => {
    useAutoLogoutNotice().show(15);

    const text = createWrapper().find('[data-testid=auto-logout-notice]').text();

    expect(text).toContain('login.auto_logout_notice');
    expect(text).toContain('15');
  });

  it('should show nothing after any other logout', () => {
    expect(createWrapper().find('[data-testid=auto-logout-notice]').exists()).toBe(false);
  });

  it('should go away when closed', async () => {
    useAutoLogoutNotice().show(15);
    const wrapper = createWrapper();

    wrapper.findComponent(AlertStub).vm.$emit('close');
    await nextTick();

    expect(get(useAutoLogoutNotice().idleMinutes)).toBeUndefined();
    expect(wrapper.find('[data-testid=auto-logout-notice]').exists()).toBe(false);
  });
});
