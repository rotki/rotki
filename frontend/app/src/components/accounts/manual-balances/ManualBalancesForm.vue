<template>
  <v-form
    ref="form"
    :value="valid"
    :class="$style.form"
    data-cy="manual-balance-form"
  >
    <v-text-field
      v-model="label"
      class="manual-balances-form__label"
      outlined
      :label="tc('manual_balances_form.fields.label')"
      :error-messages="v$.label.$errors.map(e => e.$message)"
      :disabled="pending"
      @focus="delete errors['label']"
    />

    <balance-type-input
      v-model="balanceType"
      :label="tc('manual_balances_form.fields.balance_type')"
      outlined
    />

    <v-radio-group v-model="assetMethod" class="mt-0" row :disabled="pending">
      <v-radio
        :value="0"
        :label="tc('manual_balances_form.fields.select_available_asset')"
      />
      <v-radio
        :value="1"
        :label="tc('manual_balances_form.fields.create_a_custom_asset')"
      />
    </v-radio-group>

    <asset-select
      v-if="assetMethod === 0"
      v-model="asset"
      :label="tc('common.asset')"
      class="manual-balances-form__asset"
      outlined
      :error-messages="v$.asset.$errors.map(e => get(e.$message))"
      :disabled="pending"
      @focus="delete errors['asset']"
    />

    <v-row v-else>
      <v-col class="col" md="6">
        <v-text-field
          v-model="customAssetName"
          outlined
          persistent-hint
          clearable
          :disabled="pending"
          :error-messages="v$.customAssetName.$errors.map(e => e.$message)"
          :label="t('common.name')"
        />
      </v-col>

      <v-col class="col" md="6">
        <v-text-field
          v-model="customAssetType"
          outlined
          persistent-hint
          clearable
          :disabled="pending"
          :error-messages="v$.customAssetType.$errors.map(e => e.$message)"
          :label="t('common.type')"
        />
      </v-col>
    </v-row>

    <amount-input
      v-model="amount"
      :label="tc('common.amount')"
      :error-messages="errors['amount']"
      class="manual-balances-form__amount"
      outlined
      autocomplete="off"
      :disabled="pending"
      @focus="delete errors['amount']"
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
      :error-messages="errors['location']"
      :disabled="pending"
      :label="tc('common.location')"
      @focus="delete errors['location']"
    />
  </v-form>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { PropType, Ref, watch } from 'vue';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import BalanceTypeInput from '@/components/inputs/BalanceTypeInput.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { BalanceType } from '@/services/balances/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import { useBalancesStore } from '@/store/balances';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useMessageStore } from '@/store/message';
import { TradeLocation } from '@/types/history/trade-location';
import { ManualBalance } from '@/types/manual-balances';
import { bigNumberify } from '@/utils/bignumbers';
import { toCapitalCase } from '@/utils/text';

const props = defineProps({
  edit: {
    required: false,
    type: Object as PropType<ManualBalance | null>,
    default: null
  },
  value: { required: true, type: Boolean },
  context: { required: true, type: String as PropType<BalanceType> }
});

const emit = defineEmits(['clear', 'input']);

const { t, tc } = useI18n();

const { edit, context } = toRefs(props);

const valid = ref(false);
const pending = ref(false);

const errors: Ref<{ [key: string]: string[] }> = ref({});

const id = ref<number | null>(null);
const asset = ref<string>('');
const label = ref<string>('');
const amount = ref<string>('');
const tags: Ref<string[]> = ref([]);
const location: Ref<TradeLocation> = ref(TRADE_LOCATION_EXTERNAL);
const balanceType: Ref<BalanceType> = ref(BalanceType.ASSET);
const form = ref<any>(null);

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

const saveCustomAsset = async (): Promise<string | undefined> => {
  let identifier: string | undefined = undefined;
  try {
    const id = await api.assets.addCustomAsset({
      name: get(customAssetName),
      customAssetType: get(customAssetType)
    });
    if (id) identifier = id;
  } catch (e: any) {
    setMessage({
      description: tc('asset_management.add_error', 0, { message: e.message })
    });
  }

  return identifier;
};

const save = async () => {
  set(pending, true);
  const balance: Omit<ManualBalance, 'id' | 'asset'> = {
    amount: bigNumberify(get(amount)),
    label: get(label),
    tags: get(tags),
    location: get(location),
    balanceType: get(balanceType)
  };

  let usedAsset: string = get(asset);

  if (get(assetMethod) === 1) {
    const assetIdentifier = await saveCustomAsset();

    if (assetIdentifier) {
      usedAsset = assetIdentifier;
    } else {
      set(pending, false);
      return false;
    }
  }

  const idVal = get(id);
  const isEdit = get(edit) && idVal;

  const status = await (isEdit
    ? editManualBalance({ ...balance, id: idVal, asset: usedAsset })
    : addManualBalance({ ...balance, asset: usedAsset }));

  await refreshPrices(false);
  set(pending, false);

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

const assetMethod = ref<number>(0);
const customAssetName = ref<string>('');
const customAssetType = ref<string>('');

watch(customAssetType, type => {
  set(customAssetType, toCapitalCase(type));
});

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
      requiredIf(() => get(assetMethod) === 0)
    )
  },
  customAssetName: {
    required: helpers.withMessage(
      tc('asset_form.name_non_empty'),
      requiredIf(() => get(assetMethod) === 1)
    )
  },
  customAssetType: {
    required: helpers.withMessage(
      tc('asset_form.type_non_empty'),
      requiredIf(() => get(assetMethod) === 1)
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
    label,
    customAssetName,
    customAssetType
  },
  { $autoDirty: true, $externalResults: errors }
);

watch(v$, ({ $invalid }) => {
  set(valid, !$invalid);
});

watch(valid, value => input(value));

defineExpose({
  save
});
</script>

<style module lang="scss">
.form {
  padding-top: 12px;
}
</style>
