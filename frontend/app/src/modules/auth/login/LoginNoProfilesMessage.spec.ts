import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LoginNoProfilesMessage from './LoginNoProfilesMessage.vue';

// The unit setup stubs I18nT with `true`, which renders none of its slots. Override it so
// the refresh / create-account buttons inside the message are reachable.
const I18nTStub = {
  name: 'I18nT',
  template: '<span><slot name="refresh_profiles" /><slot name="create_account" /></span>',
};

function mountMessage(loading = false): VueWrapper<InstanceType<typeof LoginNoProfilesMessage>> {
  return mount(LoginNoProfilesMessage, {
    global: { stubs: { I18nT: I18nTStub } },
    props: { loading },
  });
}

describe('modules/auth/login/LoginNoProfilesMessage', () => {
  it('should emit refresh-profiles from the first action', async () => {
    const wrapper = mountMessage();

    await wrapper.findAll('button')[0].trigger('click');

    expect(wrapper.emitted('refresh-profiles')).toHaveLength(1);
    expect(wrapper.emitted('new-account')).toBeUndefined();
  });

  it('should emit new-account from the second action', async () => {
    const wrapper = mountMessage();

    await wrapper.findAll('button')[1].trigger('click');

    expect(wrapper.emitted('new-account')).toHaveLength(1);
    expect(wrapper.emitted('refresh-profiles')).toBeUndefined();
  });

  it('should disable both actions while loading', () => {
    const wrapper = mountMessage(true);

    const buttons = wrapper.findAll('button');
    expect(buttons).toHaveLength(2);
    buttons.forEach(button => expect(button.attributes('disabled')).toBeDefined());
  });
});
