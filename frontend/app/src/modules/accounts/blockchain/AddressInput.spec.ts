import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import AddressInput from '@/modules/accounts/blockchain/AddressInput.vue';

const ADDRESS = '0x9531C059098e3d194fF87FebB587aB07B30B1306';
const OTHER_ADDRESS = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65';

/** Records what each field is handed, and lets the spec write to it as the user would. */
function fieldStub(tag: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'paste', 'blur'],
    props: ['modelValue', 'disabled', 'errorMessages'],
    template: `<${tag} :value="modelValue" :data-errors="[errorMessages ?? []].flat().join('|')" @input="$emit('update:modelValue', $event.target.value)" />`,
  };
}

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<InstanceType<typeof AddressInput>> {
  return mount(AddressInput, {
    global: {
      stubs: {
        RuiCheckbox: {
          emits: ['update:modelValue'],
          props: ['modelValue', 'disabled'],
          template: '<input type="checkbox" data-testid="multiple-toggle" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
        },
        RuiTextArea: fieldStub('textarea'),
        RuiTextField: fieldStub('input'),
        WalletAddressesImport: true,
      },
    },
    props: {
      addresses: [],
      disabled: false,
      errorMessages: {},
      multi: true,
      ...props,
    },
  });
}

describe('modules/accounts/blockchain/AddressInput', () => {
  let wrapper: VueWrapper<InstanceType<typeof AddressInput>>;

  afterEach(() => {
    wrapper?.unmount();
  });

  /** The messages the visible field shows, read off the stub that receives them. */
  function messages(): string[] {
    const value = wrapper.find('[data-testid=account-address-field]').attributes('data-errors') ?? '';
    return value === '' ? [] : value.split('|');
  }

  async function type(value: string): Promise<void> {
    await wrapper.find('[data-testid=account-address-field]').setValue(value);
    await nextTick();
  }

  async function useMultiple(): Promise<void> {
    await wrapper.find('[data-testid=multiple-toggle]').setValue(true);
    await nextTick();
  }

  /** Bound as a property rather than an attribute, so it is read off the element. */
  function shownValue(): string {
    return wrapper.find<HTMLInputElement>('[data-testid=account-address-field]').element.value;
  }

  function lastAddresses(): string[] | undefined {
    return wrapper.emitted<[string[]]>('update:addresses')?.at(-1)?.[0];
  }

  it('should reject an empty address', async () => {
    wrapper = createWrapper();

    expect(await wrapper.vm.validate()).toBe(false);
    await nextTick();

    expect(messages()).toEqual(['account_form.validation.address_non_empty']);
  });

  it('should accept an entered address', async () => {
    wrapper = createWrapper();
    await type(ADDRESS);

    expect(await wrapper.vm.validate()).toBe(true);
    await nextTick();

    expect(messages()).toEqual([]);
    expect(lastAddresses()).toEqual([ADDRESS]);
  });

  it('should reject an empty list once several addresses are being entered', async () => {
    wrapper = createWrapper();
    await useMultiple();

    expect(await wrapper.vm.validate()).toBe(false);
    await nextTick();

    // The same message, reported against whichever of the two fields is on screen.
    expect(messages()).toEqual(['account_form.validation.address_non_empty']);
  });

  it('should not require the single address while several are being entered', async () => {
    wrapper = createWrapper();
    await useMultiple();
    await type(ADDRESS);

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should split a list on commas and newlines', async () => {
    wrapper = createWrapper();
    await useMultiple();
    await type(`${ADDRESS},\n${OTHER_ADDRESS}`);

    expect(lastAddresses()).toEqual([ADDRESS, OTHER_ADDRESS]);
  });

  it('should drop a repeated address, whatever its case', async () => {
    wrapper = createWrapper();
    await useMultiple();
    await type(`${ADDRESS}\n${ADDRESS.toLowerCase()}`);

    // The first spelling wins, so the address is offered back as the user first wrote it.
    expect(lastAddresses()).toEqual([ADDRESS]);
  });

  it('should show the entry it was opened with', async () => {
    wrapper = createWrapper({ addresses: [ADDRESS] });
    await nextTick();

    expect(shownValue()).toBe(ADDRESS);
  });

  it('should leave an entered address behind when the entry mode changes, so the field on screen and what would be saved disagree until the list is edited', async () => {
    wrapper = createWrapper();
    await type(ADDRESS);
    await useMultiple();

    expect(shownValue()).toBe('');
    expect(lastAddresses()).toEqual([ADDRESS]);
    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should show the address error the backend reports against the single field', async () => {
    const errorMessages: ValidationErrors = { address: ['Account already exists'] };
    wrapper = createWrapper({ errorMessages });
    await nextTick();

    expect(messages()).toEqual(['Account already exists']);
  });

  it('should show the same error against the list, which the backend does not name', async () => {
    const errorMessages: ValidationErrors = { address: ['Account already exists'] };
    wrapper = createWrapper({ errorMessages, forceMultiple: true });
    await nextTick();

    // One flat key comes back for both fields, so it has to be fanned onto whichever is on screen.
    expect(messages()).toEqual(['Account already exists']);
  });
});
