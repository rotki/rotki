import { shallowMount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
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

    useConfirmStore().show({ alternativeAction: 'Exclude', message: 'message', primaryAction: 'Delete', secondaryAction: 'Keep it', title: 'Delete' }, vi.fn());
    await nextTick();

    const dialog = wrapper.findComponent(ConfirmDialog);
    expect(dialog.props('primaryAction')).toBe('Delete');
    expect(dialog.props('secondaryAction')).toBe('Keep it');
    expect(dialog.props('alternativeAction')).toBe('Exclude');
  });

  it('should run the alternative for the alternative button and the dismiss handler for backing out', async () => {
    const wrapper = shallowMount(AppMessages);
    const onDismiss = vi.fn();
    const onAlternative = vi.fn();
    const store = useConfirmStore();

    store.show({ alternativeAction: 'Exclude', message: 'message', title: 'Delete' }, vi.fn(), onDismiss, onAlternative);
    await nextTick();
    wrapper.findComponent(ConfirmDialog).vm.$emit('cancel');
    await flushPromises();

    expect(onDismiss).toHaveBeenCalledOnce();
    expect(onAlternative).not.toHaveBeenCalled();

    store.show({ alternativeAction: 'Exclude', message: 'message', title: 'Delete' }, vi.fn(), onDismiss, onAlternative);
    await nextTick();
    wrapper.findComponent(ConfirmDialog).vm.$emit('alternative');
    await flushPromises();

    expect(onAlternative).toHaveBeenCalledOnce();
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});
