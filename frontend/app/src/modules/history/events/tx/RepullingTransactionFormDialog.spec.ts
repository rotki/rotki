import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import RepullingTransactionFormDialog from '@/modules/history/events/tx/RepullingTransactionFormDialog.vue';

const { answerWideRepull, askingWideRepull } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    answerWideRepull: vi.fn<(proceed: boolean) => Promise<void>>(async () => Promise.resolve()),
    askingWideRepull: shallowRef<boolean>(false),
  };
});

vi.mock('@/modules/history/events/tx/use-repulling-transaction-submission', async () => {
  const { ref, shallowRef } = await import('vue');
  return {
    useRepullingTransactionSubmission: (): Record<string, unknown> => ({
      answerWideRepull,
      askingWideRepull,
      modelAccountType: shallowRef('blockchain'),
      modelErrorMessages: ref({}),
      modelEthStakingData: ref({}),
      modelFormData: ref({}),
      submit: vi.fn(),
      submitting: shallowRef<boolean>(false),
    }),
  };
});

vi.mock('@/modules/task-center/use-task-center', async () => {
  const { computed } = await import('vue');
  return {
    ActivityKind: { REPULLING: 'repulling' },
    useTaskCenter: (): Record<string, unknown> => ({ useIsActive: () => computed<boolean>(() => false) }),
  };
});

describe('repullingTransactionFormDialog', () => {
  function createWrapper(): VueWrapper<InstanceType<typeof RepullingTransactionFormDialog>> {
    return mount(RepullingTransactionFormDialog, {
      global: {
        stubs: {
          BigDialog: {
            props: ['display'],
            template: '<div v-if="display"><slot /><slot name="footer"><div data-testid="default-footer" /></slot></div>',
          },
          RepullingTransactionForm: true,
        },
      },
      props: { modelValue: true },
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(askingWideRepull, false);
  });

  it('should keep its own footer while nothing is being asked', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=repulling-wide-confirm]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=default-footer]').exists()).toBe(true);
  });

  it('should ask about a wide repull in the footer and pass the answer on', async () => {
    set(askingWideRepull, true);
    const wrapper = createWrapper();
    const question = wrapper.find('[data-testid=repulling-wide-confirm]');

    expect(question.text()).toContain('transactions.repulling.confirmation.message');
    expect(wrapper.find('[data-testid=default-footer]').exists()).toBe(false);

    await question.find('[data-testid=inline-confirm-accept]').trigger('click');
    expect(answerWideRepull).toHaveBeenLastCalledWith(true);

    await question.find('[data-testid=inline-confirm-cancel]').trigger('click');
    expect(answerWideRepull).toHaveBeenLastCalledWith(false);
  });
});
