import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import DataIssueCardActions from '@/modules/history/data-issues/components/DataIssueCardActions.vue';
import { IssueKind, IssueSeverity, IssueState } from '@/modules/history/data-issues/constants';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

function createIssue(state: IssueState): DataIssue {
  return {
    asset: 'ETH',
    autoRemediationAttempts: [],
    createdAt: 1710000100,
    groupIdentifier: null,
    id: 1,
    kind: IssueKind.REBASING_TOKEN,
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    payload: {},
    protocol: null,
    resolvedAt: null,
    severity: IssueSeverity.WARNING,
    state,
    tsEnd: 1710000000,
    tsStart: 1710000000,
  };
}

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
});

describe('dataIssueCardActions', () => {
  it('should not let the dismiss click reach the card behind it', async () => {
    const parentClick = vi.fn<() => void>();
    const Host = defineComponent({
      components: { DataIssueCardActions },
      setup: () => ({ issue: createIssue(IssueState.OPEN), parentClick }),
      template: '<div @click="parentClick"><DataIssueCardActions :issue="issue" /></div>',
    });
    const wrapper = mount(Host, { global: { stubs: { RuiMenu } } });

    await wrapper.find('[data-testid=data-issues-panel-dismiss]').trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(true);
    expect(parentClick).not.toHaveBeenCalled();
  });

  it('should ask about dismissing in the warning tone, since nothing is deleted', () => {
    const wrapper = mount(DataIssueCardActions, { global: { stubs: { RuiMenu } }, props: { issue: createIssue(IssueState.OPEN) } });

    const question = wrapper.findComponent(ConfirmPopover).props('question');
    expect(question.confirmLabel).toBe('data_issues.action.dismiss.label');
    expect(question.tone).not.toBe('error');
  });

  it('should emit dismiss only once the question is confirmed', async () => {
    const issue = createIssue(IssueState.OPEN);
    const wrapper = mount(DataIssueCardActions, { global: { stubs: { RuiMenu } }, props: { issue } });

    await wrapper.find('[data-testid=data-issues-panel-dismiss]').trigger('click');
    expect(wrapper.emitted('dismiss')).toBeUndefined();

    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');
    expect(wrapper.emitted('dismiss')).toEqual([[issue]]);
  });

  it('should keep retry visible but disabled while remediation is running', () => {
    const wrapper = mount(DataIssueCardActions, {
      props: { issue: createIssue(IssueState.AUTO_REMEDIATING) },
    });

    const retry = wrapper.find('[data-testid=data-issues-panel-retry]');
    expect(retry.exists()).toBe(true);
    expect(retry.attributes('disabled')).toBeDefined();
  });
});
