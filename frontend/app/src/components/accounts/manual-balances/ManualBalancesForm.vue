<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import ManualBalancesPriceForm from '@/components/accounts/manual-balances/ManualBalancesPriceForm.vue';
import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';
import type { ValidationErrors } from '@/types/api/errors';

const props = defineProps<{
  modelValue: RawManualBalance | ManualBalance;
  submitting: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: RawManualBalance | ManualBalance): void;
}>();

const { t } = useI18n();

const priceForm = ref<InstanceType<typeof ManualBalancesPriceForm>>();

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const asset = useSimplePropVModel(props, 'asset', emit);
const label = useSimplePropVModel(props, 'label', emit);
const balanceType = useSimplePropVModel(props, 'balanceType', emit);
const location = useSimplePropVModel(props, 'location', emit);

const tags = computed<string[]>({
  get() {
    return props.modelValue.tags ?? [];
  },
  set(tags: string[]) {
    emit('update:model-value', {
      ...props.modelValue,
      tags: tags.length > 0 ? tags : null,
    });
  },
});

const amount = computed({
  get() {
    return props.modelValue.amount.toString();
  },
  set(amount: string) {
    emit('update:model-value', {
      ...props.modelValue,
      amount: bigNumberify(amount),
    });
  },
});

const { manualLabels } = useManualBalancesStore();

const rules = {
  amount: {
    required: helpers.withMessage(t('manual_balances_form.validation.amount'), required),
  },
  label: {
    required: helpers.withMessage(t('manual_balances_form.validation.label_empty'), required),
    doesNotExist: helpers.withMessage(
      ({ $model: label }) =>
        t('manual_balances_form.validation.label_exists', {
          label,
        }),
      (label: string) => !get(manualLabels).includes(label),
    ),
  },
  asset: {
    required: helpers.withMessage(t('manual_balances_form.validation.asset'), required),
  },
  location: {
    required,
  },
};

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
    label,
    location,
  },
  { $autoDirty: true, $externalResults: errors },
);

const { setOpenDialog, setPostSubmitFunc } = useCustomAssetForm();

function postSubmit(assetId: string) {
  set(asset, assetId);
}

setPostSubmitFunc(postSubmit);

const customAssetTypes = ref<string[]>([]);

const { getCustomAssetTypes } = useAssetManagementApi();

async function openCustomAssetForm() {
  if (get(customAssetTypes).length === 0)
    set(customAssetTypes, await getCustomAssetTypes());

  setOpenDialog(true);
}

async function validate() {
  await get(v$).$validate();
}

async function savePrice() {
  await get(priceForm)?.savePrice(get(asset));
}

defineExpose({
  validate,
  savePrice,
});
</script>

<template>
  <RuiForm
    data-cy="manual-balance-form"
    class="flex flex-col gap-2"
  >
    <RuiTextField
      v-model="label"
      class="manual-balances-form__label"
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
        class="manual-balances-form__asset"
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
              <RuiIcon name="server-line" />
              <RuiIcon
                name="add-circle-line"
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
      class="manual-balances-form__amount"
      variant="outlined"
      autocomplete="off"
      :disabled="submitting"
      @blur="v$.amount.$touch()"
    />

    <TagInput
      v-model="tags"
      :label="t('manual_balances_form.fields.tags')"
      :disabled="submitting"
      class="manual-balances-form__tags"
    />

    <LocationSelector
      v-model="location"
      class="manual-balances-form__location"
      :error-messages="toMessages(v$.location)"
      :disabled="submitting"
      :label="t('common.location')"
      @blur="v$.location.$touch()"
    />

    <CustomAssetFormDialog
      :title="t('asset_management.add_title')"
      :types="customAssetTypes"
    />
  </RuiForm>
</template>
