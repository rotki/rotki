<template>
  <v-form
    ref="form"
    :value="valid"
    :class="$style.form"
    data-cy="manual-balance-form"
    @input="input"
  >
    <v-text-field
      v-model="label"
      class="manual-balances-form__label"
      outlined
      :label="$t('manual_balances_form.fields.label')"
      :error-messages="errors['label']"
      :rules="labelRules"
      :disabled="pending || !!edit"
      @focus="delete errors['label']"
    />

    <v-select
      v-model="balanceType"
      :label="$t('manual_balances_form.fields.balance_type')"
      :items="balanceTypes"
      outlined
    />

    <asset-select
      v-model="asset"
      :label="$t('manual_balances_form.fields.asset')"
      :error-messages="errors['asset']"
      class="manual-balances-form__asset"
      outlined
      :rules="assetRules"
      :disabled="pending"
      @focus="delete errors['asset']"
    />
    <amount-input
      v-model="amount"
      :label="$t('manual_balances_form.fields.amount')"
      :error-messages="errors['amount']"
      class="manual-balances-form__amount"
      outlined
      autocomplete="off"
      :disabled="pending"
      :rules="amountRules"
      @focus="delete errors['amount']"
    />
    <tag-input
      v-model="tags"
      :label="$t('manual_balances_form.fields.tags')"
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
      :label="$t('manual_balances_form.fields.location')"
      @focus="delete errors['location']"
    />
  </v-form>
</template>

<script lang="ts">
import {
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { IVueI18n } from 'vue-i18n';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { setupManualBalances } from '@/composables/balances';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import i18n from '@/i18n';
import { BalanceType, ManualBalance } from '@/services/balances/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { TradeLocation } from '@/services/history/types';
import { bigNumberify } from '@/utils/bignumbers';

const setupRules = (i18n: IVueI18n) => {
  const amountRules = [
    (v: string) => !!v || i18n.t('manual_balances_form.validation.amount')
  ];
  const assetRules = [
    (v: string) => !!v || i18n.t('manual_balances_form.validation.asset')
  ];
  const labelRules = [
    (v: string) => !!v || i18n.t('manual_balances_form.validation.label_empty')
  ];

  return {
    amountRules,
    assetRules,
    labelRules
  };
};

const ManualBalancesForm = defineComponent({
  name: 'ManualBalancesForm',
  components: { LocationSelector, TagInput, AssetSelect },
  props: {
    edit: {
      required: false,
      type: Object as PropType<ManualBalance>,
      default: null
    },
    value: { required: true, type: Boolean },
    context: { required: true, type: String as PropType<BalanceType> }
  },
  emits: ['clear', 'input'],
  setup(props, { emit }) {
    const { edit, context } = toRefs(props);

    const valid = ref(false);
    const pending = ref(false);

    const errors: Ref<{ [key: string]: string[] }> = ref({});

    const asset = ref('');
    const label = ref('');
    const amount = ref('');
    const tags: Ref<string[]> = ref([]);
    const location: Ref<TradeLocation> = ref(TRADE_LOCATION_EXTERNAL);
    const balanceType: Ref<BalanceType> = ref(BalanceType.ASSET);
    const form = ref<any>(null);

    const reset = () => {
      form.value?.reset();
      balanceType.value = context.value;
      errors.value = {};
    };

    const clear = () => {
      emit('clear');
      reset();
    };

    const input = (balance: ManualBalance) => {
      emit('input', balance);
    };

    const set = (balance: ManualBalance) => {
      asset.value = balance.asset;
      label.value = balance.label;
      amount.value = balance.amount.toString();
      tags.value = balance.tags ?? [];
      location.value = balance.location;
      balanceType.value = balance.balanceType;
    };

    watch(
      edit,
      balance => {
        if (!balance) {
          reset();
        } else {
          set(balance);
        }
      },
      { immediate: true }
    );

    const { editBalance, addBalance, manualLabels } = setupManualBalances();

    const save = async () => {
      pending.value = true;
      const balance: ManualBalance = {
        asset: asset.value,
        amount: bigNumberify(amount.value),
        label: label.value,
        tags: tags.value,
        location: location.value,
        balanceType: balanceType.value
      };
      const status = await (edit.value
        ? editBalance(balance)
        : addBalance(balance));

      pending.value = false;

      if (status.success) {
        clear();
        return true;
      }

      if (status.message) {
        const errorMessages = deserializeApiErrorMessage(status.message);
        errors.value = (errorMessages?.balances[0] as any) ?? {};
      }
      return false;
    };

    watch(label, label => {
      if (edit.value) {
        return;
      }

      const validationErrors = errors.value['label'];
      if (manualLabels.value.includes(label)) {
        if (validationErrors && validationErrors.length > 0) {
          return;
        }
        errors.value = {
          ...errors.value,
          label: [
            i18n
              .t('manual_balances_form.validation.label_exists', { label })
              .toString()
          ]
        };
      } else {
        const { label, ...data } = errors.value;
        errors.value = data;
      }
    });

    const balanceTypes = [
      {
        value: BalanceType.ASSET,
        text: i18n.t('manual_balances_form.type.asset')
      },
      {
        value: BalanceType.LIABILITY,
        text: i18n.t('manual_balances_form.type.liability')
      }
    ];

    return {
      form,
      valid,
      pending,
      errors,
      asset,
      label,
      amount,
      tags,
      location,
      balanceType,
      ...setupRules(i18n),
      balanceTypes,
      input,
      save,
      clear,
      reset
    };
  }
});
export default ManualBalancesForm;
</script>

<style module lang="scss">
.form {
  padding-top: 12px;
}
</style>
