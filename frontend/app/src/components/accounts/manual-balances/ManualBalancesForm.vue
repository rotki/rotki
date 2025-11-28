<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import ManualBalancesPriceForm from '@/components/accounts/manual-balances/ManualBalancesPriceForm.vue';
import CustomAssetFormDialog from '@/components/asset-manager/custom/CustomAssetFormDialog.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import RuiForm from '@/components/helper/RuiForm.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import BalanceTypeInput from '@/components/inputs/BalanceTypeInput.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useFormStateWatcher } from '@/composables/form';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useLocationStore } from '@/store/locations';
import { useBigNumberModel, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const modelValue = defineModel<RawManualBalance | ManualBalance>({ required: true });

defineProps<{
  submitting: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const priceForm = ref<InstanceType<typeof ManualBalancesPriceForm>>();
const openCustomAssetDialog = ref<boolean>(false);

const asset = useRefPropVModel(modelValue, 'asset');
const label = useRefPropVModel(modelValue, 'label');
const balanceType = useRefPropVModel(modelValue, 'balanceType');
const location = useRefPropVModel(modelValue, 'location');
const rawAmount = useRefPropVModel(modelValue, 'amount');

const locationTouched = ref<boolean>(false);

const tags = computed<string[]>({
  get() {
    return get(modelValue).tags ?? [];
  },
  set(tags: string[]) {
    set(modelValue, {
      ...get(modelValue),
      tags: tags.length > 0 ? tags : null,
    });
  },
});

const amount = useBigNumberModel(rawAmount);
const { manualLabels } = useManualBalanceData();
const { tradeLocations } = storeToRefs(useLocationStore());
const { assetInfo } = useAssetInfoRetrieval();

const rules = {
  amount: {
    required: helpers.withMessage(t('manual_balances_form.validation.amount'), required),
  },
  asset: {
    required: helpers.withMessage(t('manual_balances_form.validation.asset'), required),
  },
  balanceType: {},
  label: {
    doesNotExist: helpers.withMessage(
      ({ $model: label }) =>
        t('manual_balances_form.validation.label_exists', {
          label,
        }),
      (label: string) => 'identifier' in get(modelValue) || !get(manualLabels).includes(label),
    ),
    required: helpers.withMessage(t('manual_balances_form.validation.label_empty'), required),
  },
  location: {
    required,
  },
  tags: {},
};

const states = {
  amount,
  asset,
  balanceType,
  label,
  location,
  tags,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true, $externalResults: errors },
);

useFormStateWatcher(states, stateUpdated);

const customAssetTypes = ref<string[]>([]);

const { getCustomAssetTypes } = useAssetManagementApi();

async function openCustomAssetForm() {
  if (get(customAssetTypes).length === 0)
    set(customAssetTypes, await getCustomAssetTypes());

  set(openCustomAssetDialog, true);
}

async function validate(): Promise<boolean> {
  return await get(v$).$validate();
}

async function savePrice(): Promise<boolean> {
  return await get(priceForm)?.savePrice(get(asset)) || false;
}

watch(asset, (asset) => {
  if (!(asset && !('identifier' in get(modelValue)) && !get(locationTouched))) {
    return;
  }
  const info = get(assetInfo(asset));
  const evmChain = info?.evmChain;
  if (!evmChain) {
    return;
  }
  const foundLocation = get(tradeLocations).find(item => item.identifier === evmChain.split('_').join(' '));
  if (foundLocation) {
    set(location, foundLocation.identifier);
  }
});

defineExpose({
  savePrice,
  validate,
});
</script>

<template>
  <RuiForm
    data-cy="manual-balance-form"
    class="flex flex-col gap-2"
  >
    <RuiTextField
      v-model="label"
      data-cy="manual-balances-form-label"
      variant="outlined"
      color="primary"
      :label="t('manual_balances_form.fields.label')"
      :error-messages="toMessages(v$.label)"
      :disabled="submitting"
      @blur="v$.label.$touch()"
    />

    <BalanceTypeInput
      v-model="balanceType"
      :disabled="submitting"
      :label="t('manual_balances_form.fields.balance_type')"
    />

    <div class="flex items-start gap-4">
      <AssetSelect
        v-model="asset"
        :label="t('common.asset')"
        data-cy="manual-balances-form-asset"
        outlined
        :error-messages="toMessages(v$.asset)"
        :disabled="submitting"
        @blur="v$.asset.$touch()"
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
      :asset="asset"
    />

    <AmountInput
      v-model="amount"
      :label="t('common.amount')"
      :error-messages="toMessages(v$.amount)"
      data-cy="manual-balances-form-amount"
      variant="outlined"
      autocomplete="off"
      :disabled="submitting"
      @blur="v$.amount.$touch()"
    />

    <TagInput
      v-model="tags"
      :label="t('manual_balances_form.fields.tags')"
      :disabled="submitting"
      data-cy="manual-balances-form-tags"
    />

    <LocationSelector
      v-model="location"
      data-cy="manual-balances-form-location"
      :error-messages="toMessages(v$.location)"
      :disabled="submitting"
      :label="t('common.location')"
      @blur="v$.location.$touch()"
      @update:model-value="locationTouched = true"
    />

    <CustomAssetFormDialog
      v-model:open="openCustomAssetDialog"
      v-model:saved-asset-id="asset"
      :types="customAssetTypes"
    />
  </RuiForm>
</template>
