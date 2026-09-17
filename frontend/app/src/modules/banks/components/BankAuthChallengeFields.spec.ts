import type { BankAuthChallenge } from '@/modules/banks/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BankAuthChallengeFields from '@/modules/banks/components/BankAuthChallengeFields.vue';
import '@test/i18n';

const otp: BankAuthChallenge = {
  challenge: 'Enter the TAN for accounts',
  challengeData: null,
  challengeHtml: null,
  challengeMimeType: null,
  primitive: 'otp input',
  prompt: 'Enter the TAN for accounts',
};

function createWrapper(challenge: BankAuthChallenge, response = ''): VueWrapper<InstanceType<typeof BankAuthChallengeFields>> {
  return mount(BankAuthChallengeFields, { props: { challenge, response } });
}

describe('bankAuthChallengeFields', () => {
  it('should show a TAN prompt once, with the input labelled as the TAN', () => {
    const wrapper = createWrapper(otp);

    expect(wrapper.text().split('Enter the TAN for accounts')).toHaveLength(2);
    expect(wrapper.find('[data-testid=bank-auth-response]').text()).toContain('bank_settings.authentication.response');
  });

  it('should keep the prompt as the input hint when the bank sends a different challenge text', () => {
    const wrapper = createWrapper({ ...otp, challenge: 'Order 123 needs confirmation', prompt: 'Enter the TAN requested by your bank' });

    expect(wrapper.find('[data-testid=bank-auth-headline]').text()).toContain('Order 123 needs confirmation');
    expect(wrapper.find('[data-testid=bank-auth-response]').text()).toContain('Enter the TAN requested by your bank');
  });

  it('should emit the typed response', async () => {
    const wrapper = createWrapper(otp);

    await wrapper.find('[data-testid=bank-auth-response] input').setValue('123456');

    expect(wrapper.emitted('update:response')).toEqual([['123456']]);
  });

  it('should ask for no input when the bank waits for an app approval', () => {
    const wrapper = createWrapper({ ...otp, challenge: null, primitive: 'app approval poll', prompt: 'Approve the request in your banking app' });

    expect(wrapper.find('[data-testid=bank-auth-response]').exists()).toBe(false);
    expect(wrapper.text().split('Approve the request in your banking app')).toHaveLength(2);
  });

  it('should render a photo TAN graphic as an image and any other challenge data as text', () => {
    const photo = createWrapper({ ...otp, challengeData: 'iVBORw0KGgo=', challengeMimeType: 'image/png', primitive: 'challenge display' });
    const flicker = createWrapper({ ...otp, challengeData: '0248A0120', primitive: 'challenge display' });

    expect(photo.find('[data-testid=bank-auth-challenge-image]').attributes('src')).toBe('data:image/png;base64,iVBORw0KGgo=');
    expect(photo.find('[data-testid=bank-auth-challenge-data]').exists()).toBe(false);
    expect(flicker.find('[data-testid=bank-auth-challenge-image]').exists()).toBe(false);
    expect(flicker.find('[data-testid=bank-auth-challenge-data]').text()).toBe('0248A0120');
  });
});
