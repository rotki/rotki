import type { StubInstance } from '@test/utils/component-vm';
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import '@test/i18n';

interface NodeOperatorPayload {
  address: string;
  nodeOperatorId: number;
  stakingModuleId: number;
}

const addNodeOperator = vi.fn<(payload: NodeOperatorPayload) => Promise<{ message?: string }>>();

vi.mock('@/modules/staking/api/use-lido-csm-api', () => ({
  useLidoCsmApi: vi.fn().mockImplementation(() => ({ addNodeOperator })),
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

function account(address = ADDRESS): AddressAccount {
  return {
    address,
    chain: Blockchain.ETH,
    kind: 'address',
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
          // the dialog's confirm button, standing in for BigDialog's footer
          BigDialog: {
            emits: ['confirm', 'cancel'],
            name: 'BigDialog',
            props: ['display', 'action', 'loading', 'title', 'layout', 'failure', 'failureTitle'],
            template: '<div v-if="display"><slot /><button data-testid="lido-csm-submit" :disabled="action.disabled" @click="$emit(\'confirm\')" /></div>',
          },
          RuiMenuSelect: { ...inputStub('RuiMenuSelect'), props: ['modelValue', 'options', 'keyAttr', 'textAttr'] },
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

  function submitDisabled(): boolean {
    return wrapper.find('[data-testid=lido-csm-submit]').attributes('disabled') !== undefined;
  }

  async function selectAccount(accounts: AddressAccount[] = [account()]): Promise<void> {
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

  async function selectStakingModule(stakingModuleId: number): Promise<void> {
    field('lido-csm-staking-module').vm.$emit('update:modelValue', stakingModuleId);
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

    expect(addNodeOperator).toHaveBeenCalledWith({ address: ADDRESS, nodeOperatorId: 7, stakingModuleId: 3 });
    expect(wrapper.emitted('added')).toEqual([[undefined]]);
    expect(wrapper.emitted<[boolean]>('update:modelValue')?.at(-1)).toEqual([false]);
  });

  it('should offer both community staking modules, by their staking router id', () => {
    wrapper = createWrapper();

    const options: unknown = field('lido-csm-staking-module').props().options;
    assert(Array.isArray(options));
    expect(options.map(option => Reflect.get(option, 'key'))).toEqual([3, 5]);
  });

  it('should send the staking module the operator was picked from', async () => {
    wrapper = createWrapper();
    await selectAccount();
    await selectStakingModule(5);
    await typeId('1');

    await submit();

    expect(addNodeOperator).toHaveBeenCalledExactlyOnceWith({ address: ADDRESS, nodeOperatorId: 1, stakingModuleId: 5 });
  });

  it('should send nothing while the form is invalid', async () => {
    wrapper = createWrapper();
    await selectAccount();

    // The button is the gate, so a click on it does not even reach the handler.
    await submit();

    expect(submitDisabled()).toBe(true);
    expect(addNodeOperator).not.toHaveBeenCalled();
  });

  async function fillAndSubmit(): Promise<void> {
    wrapper = createWrapper();
    await selectAccount();
    await typeId('7');
    await submit();
  }

  function dialog(): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>({ name: 'BigDialog' });
  }

  it('should hand a warning returned with the add to the page as it closes', async () => {
    addNodeOperator.mockResolvedValue({ message: 'metrics unavailable' });

    await fillAndSubmit();

    expect(wrapper.emitted('added')).toEqual([['metrics unavailable']]);
    expect(wrapper.emitted<[boolean]>('update:modelValue')?.at(-1)).toEqual([false]);
  });

  describe('an add that fails', () => {
    it('should name the failure in the dialog and stay open', async () => {
      const error = new Error('offline');
      addNodeOperator.mockRejectedValue(error);

      await fillAndSubmit();

      expect(dialog().props('failure')).toBe(error);
      expect(dialog().props('failureTitle')).toBe('staking_page.lido_csm.messages.add_failed');
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
      expect(wrapper.emitted('added')).toBeUndefined();
    });

    it('should put a validation error on the field it names', async () => {
      addNodeOperator.mockRejectedValue(new ApiValidationError(JSON.stringify({ nodeOperatorId: ['unknown operator'] })));

      await fillAndSubmit();

      expect(messages('lido-csm-node-operator')).toEqual(['unknown operator']);
      expect(dialog().props('failure')).toBeUndefined();
    });

    it('should put a validation error on the address onto the account picker', async () => {
      addNodeOperator.mockRejectedValue(new ApiValidationError(JSON.stringify({ address: ['not the operator'] })));

      await fillAndSubmit();

      expect(messages('lido-csm-address')).toEqual(['not the operator']);
    });

    it('should clear the failure when the add is tried again', async () => {
      addNodeOperator.mockRejectedValueOnce(new Error('offline'));
      await fillAndSubmit();
      addNodeOperator.mockImplementationOnce(async () => new Promise(() => {}));

      await submit();

      expect(dialog().props('failure')).toBeUndefined();
    });
  });
});
