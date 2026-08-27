import type { StubInstance } from '@test/utils/component-vm';
import type { VueWrapper } from '@vue/test-utils';
import type { AddressBookPayload } from '@/modules/accounts/address-book/eth-names';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: vi.fn().mockReturnValue({
    getAddressName: vi.fn(),
    useAddressesWithoutNames: vi.fn().mockImplementation(() => computed<string[]>(() => [])),
  }),
}));

const AddressBookForm = (await import('@/modules/accounts/address-book/AddressBookForm.vue')).default;

function fieldStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'items', 'options', 'disabled'],
    template: '<div />',
  };
}

const STUBS = {
  AppImage: true,
  AutoCompleteWithSearchSync: fieldStub('AutoCompleteWithSearchSync'),
  ChainSelect: fieldStub('ChainSelect'),
  RuiMenuSelect: fieldStub('RuiMenuSelect'),
  RuiTextField: fieldStub('RuiTextField'),
};

function payload(overrides: Partial<AddressBookPayload> = {}): AddressBookPayload {
  return {
    address: '',
    blockchain: 'all',
    location: 'private',
    name: '',
    ...overrides,
  };
}

describe('modules/accounts/address-book/AddressBookForm', () => {
  let harness: ModelFormHarness<AddressBookPayload>;

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    harness?.wrapper.unmount();
  });

  function createHarness(value: AddressBookPayload = payload()): ModelFormHarness<AddressBookPayload> {
    return mountModelForm<AddressBookPayload>(AddressBookForm, {
      errors: {},
      global: { stubs: STUBS },
      payload: value,
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return harness.wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(testId: string, value: unknown): Promise<void> {
    field(testId).vm.$emit('update:modelValue', value);
    await nextTick();
  }

  it('should reject an empty form and name each missing field', async () => {
    harness = createHarness(payload({ blockchain: null }));

    expect(await harness.validate()).toBe(false);
    await nextTick();

    expect(messages('address-book-form-chain')).toEqual(['address_book.form.validation.chain']);
    expect(messages('address-book-form-address')).toEqual(['address_book.form.validation.address']);
    expect(messages('address-book-form-name')).toEqual(['address_book.form.validation.name']);
  });

  it('should accept a filled entry', async () => {
    harness = createHarness(payload({
      address: '0x9531C059098e3d194fF87FebB587aB07B30B1306',
      name: 'my wallet',
    }));

    expect(await harness.validate()).toBe(true);
    await nextTick();

    expect(messages('address-book-form-name')).toEqual([]);
  });

  it('should treat a whitespace-only entry as missing', async () => {
    harness = createHarness(payload({ address: '  ', name: '  ' }));

    expect(await harness.validate()).toBe(false);
    await nextTick();

    expect(messages('address-book-form-address')).toEqual(['address_book.form.validation.address']);
    expect(messages('address-book-form-name')).toEqual(['address_book.form.validation.name']);
  });

  it('should write an edit back to the payload the dialog saves', async () => {
    harness = createHarness();

    await edit('address-book-form-name', 'my wallet');

    expect(harness.model().name).toBe('my wallet');
  });

  it('should open without arming the unsaved-changes prompt', async () => {
    harness = createHarness();
    await nextTick();

    expect(harness.stateUpdated()).toBe(false);
  });

  it('should arm the unsaved-changes prompt on an edit, however early', async () => {
    harness = createHarness();

    await edit('address-book-form-name', 'my wallet');

    expect(harness.stateUpdated()).toBe(true);
  });

  it('should disarm the unsaved-changes prompt when the edit is undone', async () => {
    harness = createHarness();

    await edit('address-book-form-name', 'my wallet');
    await edit('address-book-form-name', '');

    expect(harness.stateUpdated()).toBe(false);
  });

  it('should not arm the unsaved-changes prompt when only the location changes, which picks the book rather than describing the entry', async () => {
    harness = createHarness();

    await edit('address-book-form-location', 'global');

    expect(harness.model().location).toBe('global');
    expect(harness.stateUpdated()).toBe(false);
  });

  it('should show a server error that is already present at mount', async () => {
    harness = mountModelForm<AddressBookPayload>(AddressBookForm, {
      errors: { name: ['Name is already taken'] },
      global: { stubs: STUBS },
      payload: payload({ address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', name: 'taken' }),
    });
    await nextTick();

    expect(messages('address-book-form-name')).toEqual(['Name is already taken']);
  });
});
