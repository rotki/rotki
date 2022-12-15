<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { type PropType, type Ref } from 'vue';
import ManualBalancesPriceForm from '@/components/accounts/manual-balances/ManualBalancesPriceForm.vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import BalanceTypeInput from '@/components/inputs/BalanceTypeInput.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { BalanceType } from '@/services/balances/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { useBalancesStore } from '@/store/balances';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useMessageStore } from '@/store/message';
import { type TradeLocation } from '@/types/history/trade-location';
import { type ManualBalance } from '@/types/manual-balances';
import { startPromise } from '@/utils';
import { bigNumberify } from '@/utils/bignumbers';
import { toMessages } from '@/utils/validation-errors';
import CustomAssetForm from '@/components/asset-manager/CustomAssetForm.vue';
import { useAssetManagementApi } from '@/services/assets/management-api';

const props = defineProps({
  edit: {
    required: false,
    type: Object as PropType<ManualBalance | null>,
    default: null
  },
  value: { required: true, type: Boolean },
  context: { required: true, type: String as PropType<BalanceType> }
});

const emit = defineEmits<{
  (e: 'clear'): void;
  (e: 'input', valid: boolean): void;
}>();

const { t, tc } = useI18n();

const { edit, context } = toRefs(props);

const pending = ref(false);

const errors: Ref<Record<string, string[]>> = ref({});

const id = ref<number | null>(null);
const asset = ref<string>('');
const label = ref<string>('');
const amount = ref<string>('');
const tags: Ref<string[]> = ref([]);
const location: Ref<TradeLocation> = ref(TRADE_LOCATION_EXTERNAL);
const balanceType: Ref<BalanceType> = ref(BalanceType.ASSET);
const form = ref<any>(null);
const priceForm: Ref<InstanceType<typeof ManualBalancesPriceForm> | null> =
  ref(null);

const reset = () => {
  get(form)?.reset();
  set(balanceType, get(context));
  set(errors, {});
};

const clear = () => {
  emit('clear');
  reset();
};

const input = (value: boolean) => {
  emit('input', value);
};

const setBalance = (balance: ManualBalance) => {
  set(id, balance.id);
  set(asset, balance.asset);
  set(label, balance.label);
  set(amount, balance.amount.toFixed());
  set(tags, balance.tags ?? []);
  set(location, balance.location);
  set(balanceType, balance.balanceType);
};

watch(
  edit,
  balance => {
    if (!balance) {
      reset();
    } else {
      setBalance(balance);
    }
  },
  { immediate: true }
);

const { editManualBalance, addManualBalance, manualLabels } =
  useManualBalancesStore();
const { refreshPrices } = useBalancesStore();
const { setMessage } = useMessageStore();

const save = async () => {
  set(pending, true);
  const balance: Omit<ManualBalance, 'id' | 'asset'> = {
    amount: bigNumberify(get(amount)),
    label: get(label),
    tags: get(tags),
    location: get(location),
    balanceType: get(balanceType)
  };

  const usedAsset: string = get(asset);

  const idVal = get(id);
  const isEdit = get(edit) && idVal;

  const form = get(priceForm);
  await form?.savePrice(usedAsset);

  const status = await (isEdit
    ? editManualBalance({ ...balance, id: idVal, asset: usedAsset })
    : addManualBalance({ ...balance, asset: usedAsset }));

  set(pending, false);
  startPromise(refreshPrices(true));

  if (status.success) {
    clear();
    return true;
  }

  if (status.message) {
    const errorMessages = deserializeApiErrorMessage(status.message);
    if (errorMessages) {
      set(errors, (errorMessages?.balances[0] as any) ?? {});
    } else {
      const obj = { message: status.message };
      setMessage({
        description: isEdit
          ? tc('actions.manual_balances.edit.error.description', 0, obj)
          : tc('actions.manual_balances.add.error.description', 0, obj)
      });
    }
  }
  return false;
};

watch(label, label => {
  if (get(edit)) {
    return;
  }

  const validationErrors = get(errors)['label'];
  if (get(manualLabels).includes(label)) {
    if (validationErrors && validationErrors.length > 0) {
      return;
    }
    set(errors, {
      ...get(errors),
      label: [
        t('manual_balances_form.validation.label_exists', {
          label
        }).toString()
      ]
    });
  } else {
    const { label, ...data } = get(errors);
    set(errors, data);
  }
});

const customAssetFormRef: Ref<InstanceType<typeof CustomAssetForm> | null> =
  ref(null);
const showCustomAssetForm: Ref<boolean> = ref(false);
const customAssetFormValid: Ref<boolean> = ref(false);
const customAssetFormSaving: Ref<boolean> = ref(false);

const customAssetTypes = ref<string[]>([]);

const { getCustomAssetTypes } = useAssetManagementApi();

const openCustomAssetForm = async () => {
  if (get(customAssetTypes).length === 0) {
    set(customAssetTypes, await getCustomAssetTypes());
  }

  set(showCustomAssetForm, true);
};

const saveCustomAsset = async () => {
  set(customAssetFormSaving, true);

  set(customAssetFormSaving, true);
  const identifier = await get(customAssetFormRef)?.save();

  if (identifier) {
    set(showCustomAssetForm, false);
    set(asset, identifier);
  }

  set(customAssetFormSaving, false);
};

const rules = {
  amount: {
    required: helpers.withMessage(
      tc('manual_balances_form.validation.amount'),
      required
    )
  },
  label: {
    required: helpers.withMessage(
      tc('manual_balances_form.validation.label_empty'),
      required
    )
  },
  asset: {
    required: helpers.withMessage(
      tc('manual_balances_form.validation.asset'),
      required
    )
  },
  location: {
    required
  }
};

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
    label,
    location
  },
  { $autoDirty: true, $externalResults: errors }
);

watch(v$, ({ $invalid }) => {
  input(!$invalid);
});

watch(asset, async asset => {
  const form = get(priceForm);
  await form?.searchAssetPrice(asset);
});

onMounted(async () => {
  const editPayload = get(edit);
  if (editPayload) {
    const form = get(priceForm);
    await form?.searchAssetPrice(editPayload.asset);
  }
});

defineExpose({
  save
});
</script>

<template>
  <v-form
    ref="form"
    :value="!v$.$invalid"
    :class="$style.form"
    data-cy="manual-balance-form"
  >
    <v-text-field
      v-model="label"
      class="manual-balances-form__label"
      outlined
      :label="tc('manual_balances_form.fields.label')"
      :error-messages="toMessages(v$.label.$errors)"
      :disabled="pending"
      @blur="v$.label.$touch()"
    />

    <balance-type-input
      v-model="balanceType"
      :disabled="pending"
      :label="tc('manual_balances_form.fields.balance_type')"
      outlined
    />

    <v-row>
      <v-col>
        <asset-select
          v-model="asset"
          :label="tc('common.asset')"
          class="manual-balances-form__asset"
          outlined
          :error-messages="toMessages(v$.asset.$errors)"
          :disabled="pending"
          @blur="v$.asset.$touch()"
        />
      </v-col>
      <v-col cols="auto">
        <v-tooltip top>
          <template #activator="{ on }">
            <v-btn
              text
              color="primary"
              class="mt-1 py-6"
              :disabled="pending"
              v-on="on"
              @click="openCustomAssetForm"
            >
              <div class="d-flex">
                <v-icon large>mdi-pencil-circle-outline</v-icon>
                <v-icon small class="mt-n4">mdi-plus</v-icon>
              </div>
            </v-btn>
          </template>
          <span>
            {{ tc('manual_balances_form.fields.create_a_custom_asset') }}
          </span>
        </v-tooltip>
      </v-col>
    </v-row>

    <manual-balances-price-form ref="priceForm" :pending="pending" />

    <amount-input
      v-model="amount"
      :label="tc('common.amount')"
      :error-messages="toMessages(v$.amount.$errors)"
      class="manual-balances-form__amount"
      outlined
      autocomplete="off"
      :disabled="pending"
      @blur="v$.amount.$touch()"
    />

    <tag-input
      v-model="tags"
      :label="tc('manual_balances_form.fields.tags')"
      :disabled="pending"
      outlined
      class="manual-balances-form__tags"
    />

    <location-selector
      v-model="location"
      class="manual-balances-form__location"
      outlined
      :error-messages="toMessages(v$.location.$errors)"
      :disabled="pending"
      :label="tc('common.location')"
      @blur="v$.location.$touch()"
    />

    <big-dialog
      :display="showCustomAssetForm"
      :title="tc('asset_management.add_title')"
      :action-disabled="!customAssetFormValid || customAssetFormSaving"
      :primary-action="tc('common.actions.save')"
      :loading="customAssetFormSaving"
      @confirm="saveCustomAsset()"
      @cancel="showCustomAssetForm = false"
    >
      <custom-asset-form
        :ref="customAssetFormRef"
        :types="customAssetTypes"
        :edit="false"
        @valid="customAssetFormValid = $event"
      />
    </big-dialog>
  </v-form>
</template>

<style module lang="scss">
.form {
  padding-top: 12px;
}
</style>
