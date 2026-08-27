import type { StubInstance } from '@test/utils/component-vm';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, describe, expect, it } from 'vitest';
import Eth2Input from '@/modules/accounts/blockchain/Eth2Input.vue';

const REQUIRED_MESSAGE = 'eth2_input.validation.required';

function textFieldStub(): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name: 'RuiTextField',
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

describe('modules/accounts/blockchain/Eth2Input', () => {
  let wrapper: VueWrapper<InstanceType<typeof Eth2Input>>;

  function createWrapper(validator: Eth2Validator = {}, errorMessages: ValidationErrors = {}): VueWrapper<InstanceType<typeof Eth2Input>> {
    const created = mount(Eth2Input, {
      global: {
        stubs: {
          RuiTextField: textFieldStub(),
        },
      },
      props: {
        disabled: false,
        editMode: false,
        errorMessages,
        validator,
      },
    });
    return created;
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(testId: string, value: string): Promise<void> {
    field(testId).vm.$emit('update:modelValue', value);
    await nextTick();
  }

  it('should emit nothing until something is typed, then emit the whole payload including the blanks', async () => {
    wrapper = createWrapper();
    await nextTick();

    expect(wrapper.emitted('update:validator')).toBeUndefined();

    await edit('eth2-validator-index', '123');

    expect(wrapper.emitted('update:validator')?.at(-1)).toEqual([{
      ownershipPercentage: '',
      publicKey: '',
      validatorIndex: '123',
    }]);
  });

  it('should reject an empty form and mark both sides of the pair as required', async () => {
    wrapper = createWrapper();

    expect(wrapper.vm.validate()).toBe(false);
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual([REQUIRED_MESSAGE]);
    expect(messages('eth2-public-key')).toEqual([REQUIRED_MESSAGE]);
    expect(messages('eth2-ownership-percentage')).toEqual([]);
  });

  it('should accept a validator index alone', async () => {
    wrapper = createWrapper();
    await edit('eth2-validator-index', '123');

    expect(wrapper.vm.validate()).toBe(true);
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual([]);
    expect(messages('eth2-public-key')).toEqual([]);
  });

  it('should accept a public key alone', async () => {
    wrapper = createWrapper();
    await edit('eth2-public-key', '0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c');

    expect(wrapper.vm.validate()).toBe(true);
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual([]);
    expect(messages('eth2-public-key')).toEqual([]);
  });

  it('should reject a non-numeric validator index without also calling it missing', async () => {
    wrapper = createWrapper();
    await edit('eth2-validator-index', 'abc');

    expect(wrapper.vm.validate()).toBe(false);
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual(['eth2_input.validator_index.validation']);
    expect(messages('eth2-public-key')).toEqual([]);
  });

  it.each([
    ['0', false],
    ['101', false],
    ['-1', false],
    ['100', true],
    ['0.5', true],
    ['', true],
  ])('should treat an ownership percentage of "%s" as valid=%s', async (percentage, valid) => {
    wrapper = createWrapper();
    await edit('eth2-validator-index', '123');
    await edit('eth2-ownership-percentage', percentage);

    expect(wrapper.vm.validate()).toBe(valid);
    await nextTick();

    expect(messages('eth2-ownership-percentage')).toEqual(valid ? [] : ['eth2_input.ownership.validation']);
  });

  it('should show a server error that is already present at mount', async () => {
    wrapper = createWrapper({ validatorIndex: '123' }, { validatorIndex: ['Validator 123 is already tracked'] });
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual(['Validator 123 is already tracked']);
  });

  it('should show a server error that arrives after mount, without making the form invalid', async () => {
    wrapper = createWrapper({ validatorIndex: '123' });
    await wrapper.setProps({ errorMessages: { validatorIndex: ['Validator 123 is already tracked'] } });
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual(['Validator 123 is already tracked']);
    expect(wrapper.vm.validate()).toBe(true);
  });

  it('should report both rules against a whitespace-only index, in rule order, and leave the public key unflagged', async () => {
    wrapper = createWrapper({ validatorIndex: ' ' });

    expect(wrapper.vm.validate()).toBe(false);
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual([
      'eth2_input.validator_index.validation',
      REQUIRED_MESSAGE,
    ]);
    expect(messages('eth2-public-key')).toEqual([]);
  });
});
