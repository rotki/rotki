import { shallowMount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirm } from '@/modules/core/common/use-confirm';
import AppMessages from '@/modules/shell/app/AppMessages.vue';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

vi.mock('@/modules/accounts/address-book/use-address-book-form', () => ({
  useAddressBookForm: (): object => ({ globalPayload: ref(), openDialog: ref(false) }),
}));

vi.mock('@/modules/auth/use-auto-login', () => ({
  useAutoLogin: (): object => ({ confirmPassword: vi.fn(), needsPasswordConfirmation: ref(false), username: ref('') }),
}));

vi.mock('@/modules/core/common/use-report-issue', () => ({
  useReportIssue: (): object => ({ visible: ref(false) }),
}));

vi.mock('@/modules/shell/app/use-backend-messages', () => ({
  useBackendMessages: (): object => ({ isMacOsVersionUnsupported: ref(false), isWinVersionUnsupported: ref(false), startupErrorMessage: ref('') }),
}));

describe('modules/shell/app/AppMessages', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should hand a confirmation\'s own button labels to the dialog, the dismiss label included', async () => {
    const wrapper = shallowMount(AppMessages);

    const answer = useConfirm().ask({ alternativeAction: 'Exclude', message: 'message', primaryAction: 'Delete', secondaryAction: 'Keep it', title: 'Delete' });
    await nextTick();

    const dialog = wrapper.findComponent(ConfirmDialog);
    expect(dialog.props('primaryAction')).toBe('Delete');
    expect(dialog.props('secondaryAction')).toBe('Keep it');
    expect(dialog.props('alternativeAction')).toBe('Exclude');
    dialog.vm.$emit('cancel');
    await answer;
  });

  it('should answer the question with how the dialog was closed: backing out, the alternative, or confirm', async () => {
    const wrapper = shallowMount(AppMessages);
    const { ask } = useConfirm();

    for (const [event, choice] of [['cancel', 'dismiss'], ['alternative', 'alternative'], ['confirm', 'confirm']] as const) {
      const answer = ask({ alternativeAction: 'Exclude', message: 'message', title: 'Delete' });
      await nextTick();
      wrapper.findComponent(ConfirmDialog).vm.$emit(event);
      await expect(answer).resolves.toBe(choice);
    }
  });
});
