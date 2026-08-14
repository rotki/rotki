<script setup lang="ts">
import type { ZodType } from 'zod';
import type { ManualBalance, RawManualBalance } from '@/modules/balances/types/manual-balances';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import {
  type ManualBalanceFormState,
  manualBalanceSchema,
  toFormState,
  toPayload,
} from '@/modules/accounts/manual-balances/manual-balance-form';
import ManualBalancesPriceForm from '@/modules/accounts/manual-balances/ManualBalancesPriceForm.vue';
import { useSuggestedLocation } from '@/modules/accounts/manual-balances/use-suggested-location';
import CustomAssetFormDialog from '@/modules/assets/admin/custom/CustomAssetFormDialog.vue';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useModelForm } from '@/modules/core/form/use-model-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import BalanceTypeInput from '@/modules/shell/components/inputs/BalanceTypeInput.vue';
import TagInput from '@/modules/shell/components/inputs/TagInput.vue';

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const modelValue = defineModel<RawManualBalance | ManualBalance>({ required: true });

defineProps<{
  submitting: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const priceForm = useTemplateRef<InstanceType<typeof ManualBalancesPriceForm>>('priceForm');
const openCustomAssetDialog = ref<boolean>(false);

const { manualLabels } = useManualBalanceData();

const editing = computed<boolean>(() => 'identifier' in get(modelValue));

const schema = computed<ZodType>(() => manualBalanceSchema({
  amount: t('manual_balances_form.validation.amount'),
  asset: t('manual_balances_form.validation.asset'),
  labelEmpty: t('manual_balances_form.validation.label_empty'),
  labelExists: (label: string) => t('manual_balances_form.validation.label_exists', { label }),
  location: t('manual_balances_form.validation.location'),
}, {
  editing: get(editing),
  takenLabels: get(manualLabels),
}));

/** The amount is text while it is typed and the tags use null for "none", so the two differ. */
const formModel = computed<ManualBalanceFormState>({
  get() {
    return toFormState(get(modelValue));
  },
  set(state: ManualBalanceFormState) {
    set(modelValue, toPayload(get(modelValue), state));
  },
});

const { errors: fieldErrors, state, touch, validate } = useModelForm<ManualBalanceFormState>({
  model: formModel,
  schema,
  serverErrors: errors,
  stateUpdated,
});

const { markChosen } = useSuggestedLocation(() => state.asset, {
  apply: (location: string): void => {
    state.location = location;
  },
  editing,
});

const customAssetTypes = ref<string[]>([]);

const { getCustomAssetTypes } = useAssetManagementApi();

async function openCustomAssetForm(): Promise<void> {
  if (get(customAssetTypes).length === 0)
    set(customAssetTypes, await getCustomAssetTypes());

  set(openCustomAssetDialog, true);
}

async function savePrice(): Promise<boolean> {
  return await get(priceForm)?.savePrice(state.asset) || false;
}

defineExpose({
  savePrice,
  validate,
});
</script>

<template>
  <div
    data-testid="manual-balance-form"
    class="flex flex-col gap-2"
  >
    <RuiTextField
      v-model="state.label"
      data-testid="manual-balances-form-label"
      variant="outlined"
      color="primary"
      :label="t('manual_balances_form.fields.label')"
      :error-messages="fieldErrors('label')"
      :disabled="submitting"
      @update:model-value="touch('label')"
    />

    <BalanceTypeInput
      v-model="state.balanceType"
      :disabled="submitting"
      :label="t('manual_balances_form.fields.balance_type')"
    />

    <div class="flex items-start gap-4">
      <AssetSelect
        v-model="state.asset"
        :label="t('common.asset')"
        data-testid="manual-balances-form-asset"
        outlined
        :source="{ chain: state.location }"
        :error-messages="fieldErrors('asset')"
        :disabled="submitting"
        @update:model-value="touch('asset')"
      />
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            type="button"
            color="primary"
            class="pt-5 pb-2 mt-1 px-2"
            :disabled="submitting"
            @click="openCustomAssetForm()"
          >
            <div class="flex">
              <RuiIcon name="lu-server" />
              <RuiIcon
                name="lu-circle-plus"
                class="-mt-4 -ml-2"
              />
            </div>
          </RuiButton>
        </template>
        <span>
          {{ t('manual_balances_form.fields.create_a_custom_asset') }}
        </span>
      </RuiTooltip>
    </div>

    <ManualBalancesPriceForm
      ref="priceForm"
      :pending="submitting"
      :asset="state.asset"
    />

    <AmountInput
      v-model="state.amount"
      :label="t('common.amount')"
      :error-messages="fieldErrors('amount')"
      data-testid="manual-balances-form-amount"
      variant="outlined"
      autocomplete="off"
      :disabled="submitting"
      @update:model-value="touch('amount')"
    />

    <TagInput
      v-model="state.tags"
      :label="t('manual_balances_form.fields.tags')"
      :disabled="submitting"
      data-testid="manual-balances-form-tags"
    />

    <LocationSelector
      v-model="state.location"
      data-testid="manual-balances-form-location"
      :error-messages="fieldErrors('location')"
      :disabled="submitting"
      :label="t('common.location')"
      @update:model-value="touch('location'); markChosen()"
    />

    <CustomAssetFormDialog
      v-model:open="openCustomAssetDialog"
      v-model:saved-asset-id="state.asset"
      :types="customAssetTypes"
    />
  </div>
</template>
