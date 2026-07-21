import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ReportIssueEmailButton from '@/modules/shell/components/ReportIssueEmailButton.vue';

interface Props {
  email?: string;
  isFormValid?: boolean;
}

function mountEmailButton(props: Props = {}): VueWrapper<InstanceType<typeof ReportIssueEmailButton>> {
  return mount(ReportIssueEmailButton, {
    props: { email: 'support@rotki.com', isFormValid: true, ...props },
  });
}

describe('modules/shell/components/ReportIssueEmailButton', () => {
  it('should emit submit-email when the email button is clicked', async () => {
    const wrapper = mountEmailButton();
    await wrapper.find('[data-testid=submit-email]').trigger('click');
    expect(wrapper.emitted('submit-email')).toHaveLength(1);
  });

  it('should disable the email button when the form is invalid', () => {
    const wrapper = mountEmailButton({ isFormValid: false });
    expect(wrapper.find('[data-testid=submit-email]').attributes('disabled')).toBeDefined();
  });
});
