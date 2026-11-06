import type { AddTransactionHashPayload } from '@/modules/history/events/event-payloads';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import TransactionFormDialog from '@/modules/history/events/tx/TransactionFormDialog.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

type AddResult = { success: true } | { success: false; message?: string | Record<string, string[]> };

const { spies } = vi.hoisted(() => ({
  spies: {
    addTransactionHash: vi.fn<(payload: object) => Promise<AddResult>>(),
    validate: vi.fn<() => Promise<boolean>>(),
  },
}));

vi.mock('@/modules/history/events/tx/use-history-transactions', () => ({
  useHistoryTransactions: (): object => ({ addTransactionHash: spies.addTransactionHash }),
}));

const FormStub = defineComponent({
  name: 'TransactionForm',
  props: { errorMessages: { default: () => ({}), type: Object } },
  setup(_props, { expose }) {
    expose({ validate: spies.validate });
    return {};
  },
  template: '<div />',
});

const PAYLOAD: AddTransactionHashPayload = {
  associatedAddress: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
  blockchain: 'eth',
  txRef: '0xabc',
};

function createWrapper(): VueWrapper<InstanceType<typeof TransactionFormDialog>> {
  return mount(TransactionFormDialog, {
    global: {
      stubs: {
        BigDialog: {
          emits: ['confirm', 'cancel'],
          props: ['display', 'failure', 'failureTitle', 'loading', 'title'],
          template: '<div v-if="display"><slot /></div>',
        },
        TransactionForm: FormStub,
      },
    },
    props: { modelValue: { ...PAYLOAD } },
  });
}

async function save(wrapper: VueWrapper): Promise<void> {
  wrapper.findComponent(BigDialog).vm.$emit('confirm');
  await flushPromises();
}

describe('transactionFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.validate.mockResolvedValue(true);
    spies.addTransactionHash.mockResolvedValue({ success: true });
  });

  it('should close and ask for the transaction to be reloaded once added', async () => {
    const wrapper = createWrapper();

    await save(wrapper);

    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    expect(wrapper.emitted('reload')).toEqual([[{ location: 'eth', txRef: '0xabc' }]]);
  });

  it('should hand field errors back to the form and name no failure', async () => {
    spies.addTransactionHash.mockResolvedValue({ message: { txRef: ['not found'] }, success: false });
    const wrapper = createWrapper();

    await save(wrapper);

    expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual({ txRef: ['not found'] });
    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
  });

  it('should name a failure that blames no field in the dialog, which stays open', async () => {
    spies.addTransactionHash.mockResolvedValue({ message: 'node unreachable', success: false });
    const wrapper = createWrapper();

    await save(wrapper);

    const dialog = wrapper.findComponent(BigDialog);
    expect(dialog.props('failure')).toBe('node unreachable');
    expect(dialog.props('failureTitle')).toBe('transactions.dialog.add_tx_error');
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should drop the failure when the next save starts', async () => {
    spies.addTransactionHash.mockResolvedValueOnce({ message: 'node unreachable', success: false });
    const wrapper = createWrapper();

    await save(wrapper);
    await save(wrapper);

    expect(wrapper.findComponent(BigDialog).props('failure')).toBeUndefined();
  });
});
