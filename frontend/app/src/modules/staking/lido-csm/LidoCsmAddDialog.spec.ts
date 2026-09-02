import type { StubInstance } from '@test/utils/component-vm';
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

interface NodeOperatorPayload {
  address: string;
  nodeOperatorId: number;
}

const addNodeOperator = vi.fn<(payload: NodeOperatorPayload) => Promise<{ message?: string }>>();
const setMessage = vi.fn();

vi.mock('@/modules/staking/api/use-lido-csm-api', () => ({
  useLidoCsmApi: vi.fn().mockImplementation(() => ({ addNodeOperator })),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: vi.fn().mockImplementation(() => ({ setMessage })),
}));

const LidoCsmAddDialog = (await import('@/modules/staking/lido-csm/LidoCsmAddDialog.vue')).default;

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

const ADDRESS = '0x9531C059098e3d194fF87FebB587aB07B30B1306';

function account(address = ADDRESS): BlockchainAccount<AddressData> {
  return {
    chain: Blockchain.ETH,
    data: { address, type: 'address' },
    nativeAsset: 'ETH',
  };
}

describe('lidoCsmAddDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof LidoCsmAddDialog>>;

  beforeEach(() => {
    vi.clearAllMocks();
    addNodeOperator.mockResolvedValue({});
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(): VueWrapper<InstanceType<typeof LidoCsmAddDialog>> {
    return mount(LidoCsmAddDialog, {
      global: {
        stubs: {
          BlockchainAccountSelector: {
            emits: ['update:modelValue', 'blur'],
            name: 'BlockchainAccountSelector',
            props: ['modelValue', 'field', 'source'],
            template: '<div />',
          },
          RuiCard: {
            name: 'RuiCard',
            template: '<div><slot name="header" /><slot /><slot name="footer" /></div>',
          },
          RuiDialog: {
            name: 'RuiDialog',
            props: ['modelValue'],
            template: '<div><slot v-if="modelValue" /></div>',
          },
          RuiTextField: inputStub('RuiTextField'),
        },
      },
      props: { modelValue: true },
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(testId: string): string[] {
    const props = field(testId).props();
    const bag: unknown = props.field;
    const value: unknown = typeof bag === 'object' && bag !== null
      ? Reflect.get(bag, 'errorMessages')
      : props.errorMessages;
    assert(Array.isArray(value));
    return value.map(String);
  }

  function submitDisabled(): unknown {
    return wrapper.findComponent<StubInstance>('[data-testid=lido-csm-submit]').props('disabled');
  }

  async function selectAccount(accounts: BlockchainAccount<AddressData>[] = [account()]): Promise<void> {
    const input = field('lido-csm-address');
    input.vm.$emit('update:modelValue', accounts);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  async function typeId(value: string): Promise<void> {
    const input = field('lido-csm-node-operator');
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  async function submit(): Promise<void> {
    await wrapper.find('[data-testid=lido-csm-submit]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should show no message before anything is touched', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('lido-csm-address')).toEqual([]);
    expect(messages('lido-csm-node-operator')).toEqual([]);
  });

  it('should block the submit until both fields are filled', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(submitDisabled()).toBe(true);

    await selectAccount();
    expect(submitDisabled()).toBe(true);

    await typeId('5');
    expect(submitDisabled()).toBe(false);
  });

  it('should block the submit on the address alone', async () => {
    wrapper = createWrapper();
    await typeId('5');

    expect(submitDisabled()).toBe(true);

    await selectAccount();
    expect(submitDisabled()).toBe(false);
  });

  it('should accept a zero node operator id', async () => {
    wrapper = createWrapper();
    await selectAccount();

    await typeId('0');

    expect(submitDisabled()).toBe(false);
  });

  it('should report the missing address once the selection is cleared', async () => {
    wrapper = createWrapper();
    await selectAccount();

    await selectAccount([]);

    expect(messages('lido-csm-address')).toEqual(['staking_page.lido_csm.form.validation.non_empty_address']);
  });

  it('should report the missing id once the field is emptied', async () => {
    wrapper = createWrapper();
    await selectAccount();
    await typeId('5');

    await typeId('');

    expect(messages('lido-csm-node-operator')).toEqual(['staking_page.lido_csm.form.validation.non_empty_id']);
  });

  it('should treat a whitespace-only id as missing, and not as a bad number', async () => {
    wrapper = createWrapper();
    await selectAccount();

    await typeId('   ');

    // Number('   ') is 0, so the numeric rule is satisfied; only the missing-value rule fires.
    expect(messages('lido-csm-node-operator')).toEqual(['staking_page.lido_csm.form.validation.non_empty_id']);
  });

  it('should report an invalid id while typing, before the field is left', async () => {
    wrapper = createWrapper();
    await selectAccount();

    field('lido-csm-node-operator').vm.$emit('update:modelValue', 'abc');
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('lido-csm-node-operator')).toEqual(['staking_page.lido_csm.form.validation.invalid_id']);
  });

  it.each([
    ['abc'],
    ['1.5'],
    ['-1'],
  ])('should reject %s as a node operator id', async (value) => {
    wrapper = createWrapper();
    await selectAccount();

    await typeId(value);

    expect(messages('lido-csm-node-operator')).toEqual(['staking_page.lido_csm.form.validation.invalid_id']);
    expect(submitDisabled()).toBe(true);
  });

  it('should send the selected address and the id as a number', async () => {
    wrapper = createWrapper();
    await selectAccount();
    await typeId('7');

    await submit();

    expect(addNodeOperator).toHaveBeenCalledWith({ address: ADDRESS, nodeOperatorId: 7 });
    expect(wrapper.emitted('refresh')).toBeTruthy();
    expect(wrapper.emitted<[boolean]>('update:modelValue')?.at(-1)).toEqual([false]);
  });

  it('should send nothing while the form is invalid', async () => {
    wrapper = createWrapper();
    await selectAccount();

    // The button is the gate, so a click on it does not even reach the handler.
    await submit();

    expect(submitDisabled()).toBe(true);
    expect(addNodeOperator).not.toHaveBeenCalled();
  });

  it('should surface a message returned by the api', async () => {
    addNodeOperator.mockResolvedValue({ message: 'already tracked' });
    wrapper = createWrapper();
    await selectAccount();
    await typeId('7');

    await submit();

    expect(setMessage).toHaveBeenCalledWith({ description: 'already tracked' });
  });

  it('should surface a thrown error', async () => {
    addNodeOperator.mockRejectedValue(new Error('offline'));
    wrapper = createWrapper();
    await selectAccount();
    await typeId('7');

    await submit();

    expect(setMessage).toHaveBeenCalledWith({
      description: 'staking_page.lido_csm.messages.add_failed::offline',
    });
  });
});
