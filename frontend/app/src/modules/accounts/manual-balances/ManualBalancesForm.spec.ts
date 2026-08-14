import type { VueWrapper } from '@vue/test-utils';
import type { ComponentPublicInstance } from 'vue';
import type { ManualBalance, RawManualBalance } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';

const manualLabels = ref<string[]>([]);
const assetInfo = ref<{ evmChain?: string }>({});
const tradeLocations = ref<{ identifier: string }[]>([]);

vi.mock('@/modules/balances/manual/use-manual-balance-data', () => ({
  useManualBalanceData: vi.fn().mockReturnValue({
    manualLabels: computed<string[]>(() => get(manualLabels)),
  }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    getAssetInfo: vi.fn().mockImplementation(() => get(assetInfo)),
  }),
}));

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: vi.fn().mockReturnValue({
    getCustomAssetTypes: vi.fn().mockResolvedValue([]),
  }),
}));

// Reactive rather than a plain object: `storeToRefs` only picks up a key whose raw value is a ref,
// and only hands back the array through a proxy that unwraps it.
vi.mock('@/modules/core/common/use-location-store', () => ({
  useLocationStore: vi.fn().mockImplementation(() => reactive({
    tradeLocations: computed(() => get(tradeLocations)),
  })),
}));

const ManualBalancesForm = (await import('@/modules/accounts/manual-balances/ManualBalancesForm.vue')).default;

/** The stubs declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function fieldStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'label', 'chain'],
    template: '<div />',
  };
}

const STUBS = {
  AmountInput: fieldStub('AmountInput'),
  AssetSelect: fieldStub('AssetSelect'),
  BalanceTypeInput: fieldStub('BalanceTypeInput'),
  CustomAssetFormDialog: true,
  LocationSelector: fieldStub('LocationSelector'),
  ManualBalancesPriceForm: true,
  RuiButton: true,
  RuiIcon: true,
  RuiTextField: fieldStub('RuiTextField'),
  RuiTooltip: true,
  TagInput: fieldStub('TagInput'),
};

/** What the balances page hands the dialog for a new entry: a zero amount and a default location. */
function payload(overrides: Partial<RawManualBalance> = {}): RawManualBalance {
  return {
    amount: bigNumberify(0),
    asset: '',
    balanceType: BalanceType.ASSET,
    label: '',
    location: 'external',
    tags: null,
    ...overrides,
  };
}

function filled(): RawManualBalance {
  return payload({
    amount: bigNumberify(10),
    asset: 'ETH',
    label: 'my wallet',
    location: 'external',
  });
}

describe('modules/accounts/manual-balances/ManualBalancesForm', () => {
  let harness: ModelFormHarness<RawManualBalance | ManualBalance>;

  beforeEach(() => {
    setActivePinia(createPinia());
    set(manualLabels, []);
    set(assetInfo, {});
    set(tradeLocations, []);
  });

  afterEach(() => {
    harness?.wrapper.unmount();
  });

  function createHarness(
    value: RawManualBalance | ManualBalance = payload(),
    errors: Record<string, string[]> = {},
  ): ModelFormHarness<RawManualBalance | ManualBalance> {
    return mountModelForm<RawManualBalance | ManualBalance>(ManualBalancesForm, {
      errors,
      global: { stubs: STUBS },
      payload: value,
      props: { submitting: false },
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

  it('should reject a new balance with nothing filled in', async () => {
    harness = createHarness();

    expect(await harness.validate()).toBe(false);
    await nextTick();

    expect(messages('manual-balances-form-label')).toEqual(['manual_balances_form.validation.label_empty']);
    expect(messages('manual-balances-form-asset')).toEqual(['manual_balances_form.validation.asset']);
    // The page opens the dialog with a zero amount and a default location, so neither of those two
    // rules can fire until the user clears the field.
    expect(messages('manual-balances-form-amount')).toEqual([]);
    expect(messages('manual-balances-form-location')).toEqual([]);
  });

  it('should reject a cleared amount and location', async () => {
    harness = createHarness(filled());

    await edit('manual-balances-form-amount', '');
    await edit('manual-balances-form-location', '');

    expect(await harness.validate()).toBe(false);
    await nextTick();

    expect(messages('manual-balances-form-amount')).toEqual(['manual_balances_form.validation.amount']);
    // FLIP: the rule carried no message of its own, so vuelidate's untranslated "Value is required"
    // showed here. It has a key of its own now, saying which field is meant.
    expect(messages('manual-balances-form-location')).toEqual(['manual_balances_form.validation.location']);
  });

  it('should accept a filled balance', async () => {
    harness = createHarness(filled());

    expect(await harness.validate()).toBe(true);
    await nextTick();

    expect(messages('manual-balances-form-label')).toEqual([]);
  });

  it('should reject a label another balance already uses', async () => {
    set(manualLabels, ['my wallet']);
    harness = createHarness(filled());

    expect(await harness.validate()).toBe(false);
    await nextTick();

    expect(messages('manual-balances-form-label')).toEqual([
      'manual_balances_form.validation.label_exists::my wallet',
    ]);
  });

  it('should let an edited balance keep its own label', async () => {
    set(manualLabels, ['my wallet']);
    harness = createHarness({ ...filled(), identifier: 4 });

    // The uniqueness check is skipped entirely while editing, so the label it already holds - and
    // any other taken one - passes.
    expect(await harness.validate()).toBe(true);
    await nextTick();

    expect(messages('manual-balances-form-label')).toEqual([]);
  });

  it('should suggest the location that matches the asset chain', async () => {
    set(assetInfo, { evmChain: 'arbitrum_one' });
    set(tradeLocations, [{ identifier: 'arbitrum one' }]);
    harness = createHarness();

    await edit('manual-balances-form-asset', 'ARB');

    expect(harness.model().location).toBe('arbitrum one');
  });

  it('should not overrule a location the user chose', async () => {
    set(assetInfo, { evmChain: 'arbitrum_one' });
    set(tradeLocations, [{ identifier: 'arbitrum one' }]);
    harness = createHarness();

    await edit('manual-balances-form-location', 'kraken');
    await edit('manual-balances-form-asset', 'ARB');

    expect(harness.model().location).toBe('kraken');
  });

  it('should not suggest a location while editing', async () => {
    set(assetInfo, { evmChain: 'arbitrum_one' });
    set(tradeLocations, [{ identifier: 'arbitrum one' }]);
    harness = createHarness({ ...filled(), identifier: 4 });

    await edit('manual-balances-form-asset', 'ARB');

    expect(harness.model().location).toBe('external');
  });

  it('should arm the unsaved-changes prompt on an edit, however early', async () => {
    harness = createHarness();

    // FLIP: `useFormStateWatcher` installed its watcher behind a 500 ms timer and never saw an
    // edit made before it arrived.
    await edit('manual-balances-form-label', 'my wallet');

    expect(harness.stateUpdated()).toBe(true);
  });

  it('should show a server error that is already present at mount', async () => {
    harness = createHarness(filled(), { label: ['Label is already taken'] });
    await nextTick();

    // FLIP: external results reached `$errors` only once the field was dirty, which is why the
    // dialog validates again after a failed save.
    expect(messages('manual-balances-form-label')).toEqual(['Label is already taken']);
  });

  it('should write an edit back to the payload the dialog saves', async () => {
    harness = createHarness();

    await edit('manual-balances-form-label', 'my wallet');
    await edit('manual-balances-form-amount', '25');

    expect(harness.model().label).toBe('my wallet');
    expect(harness.model().amount.toString()).toBe('25');
  });
});
