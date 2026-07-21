import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ReportIssueDiscordTip from '@/modules/shell/components/ReportIssueDiscordTip.vue';

function mountDiscordTip(): VueWrapper<InstanceType<typeof ReportIssueDiscordTip>> {
  return mount(ReportIssueDiscordTip);
}

describe('modules/shell/components/ReportIssueDiscordTip', () => {
  it('should render the discord tip title', () => {
    const wrapper = mountDiscordTip();
    expect(wrapper.text()).toContain('help_sidebar.report_issue.dialog.tips.discord.title');
  });

  it('should emit open-discord when the action button is clicked', async () => {
    const wrapper = mountDiscordTip();
    await wrapper.find('button').trigger('click');
    expect(wrapper.emitted('open-discord')).toHaveLength(1);
  });
});
