import type { ComponentPublicInstance } from 'vue';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it } from 'vitest';
import Eth2Input from '@/modules/accounts/blockchain/Eth2Input.vue';

/**
 * The index and the public key are a mutually exclusive pair: each is required unless the other is
 * filled, and the check trims the value it guards but not the companion it reads, so the two sides
 * do not agree on what whitespace means. Pinned below, since a schema-level refine has to decide.
 *
 * Written against the vuelidate rules and carried across the zod swap unchanged apart from three
 * deliberate flips, each marked where it is asserted.
 */

/** Was vuelidate's untranslated fallback; now a key of ours, with the same English behind it. */
const REQUIRED_MESSAGE = 'eth2_input.validation.required';

/** The stubs declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

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
    return mount(Eth2Input, {
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

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should leave the payload alone until something is typed', async () => {
    wrapper = createWrapper();
    await nextTick();

    // The dialog above arms its unsaved-changes prompt on any change to the payload, so a form
    // that filled in its own blanks at mount would prompt on close without the user typing.
    expect(wrapper.emitted('update:validator')).toBeUndefined();

    await edit('eth2-validator-index', '123');

    // One edit hands back the whole state, blanks included. The add endpoint strips the empty
    // fields, and an edit opens with all three already filled, so neither reaches the api.
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

    // FLIP: under vuelidate this rendered nothing. External results reached `$errors` only once the
    // field was dirty, and the watch that revalidated on incoming errors was not immediate, so a
    // failed save the dialog was already holding stayed invisible until something touched the field.
    expect(messages('eth2-validator-index')).toEqual(['Validator 123 is already tracked']);
  });

  it('should show a server error that arrives after mount', async () => {
    wrapper = createWrapper({ validatorIndex: '123' });
    await wrapper.setProps({ errorMessages: { validatorIndex: ['Validator 123 is already tracked'] } });
    await nextTick();

    expect(messages('eth2-validator-index')).toEqual(['Validator 123 is already tracked']);
    // FLIP: a server error no longer makes the form itself invalid, because the core keys them
    // separately from the schema. Unobservable through the dialog, which clears the errors it holds
    // before it validates, so a retry was never blocked by one under vuelidate either.
    expect(wrapper.vm.validate()).toBe(true);
  });

  it('should report both rules against a whitespace-only index, in rule order', async () => {
    wrapper = createWrapper({ validatorIndex: ' ' });

    expect(wrapper.vm.validate()).toBe(false);
    await nextTick();

    // `consistOfNumbers` guards on `!value`, and `' '` is truthy, so it fails alongside the
    // required rule. The companion `requiredUnless` on the public key reads the index untrimmed,
    // so whitespace counts as filled there and the key stays unflagged.
    expect(messages('eth2-validator-index')).toEqual([
      'eth2_input.validator_index.validation',
      REQUIRED_MESSAGE,
    ]);
    expect(messages('eth2-public-key')).toEqual([]);
  });
});
