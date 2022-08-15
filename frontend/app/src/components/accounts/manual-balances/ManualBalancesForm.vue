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
      :disabled="pending"
      @focus="delete errors['label']"
    />

    <balance-type-input
      v-model="balanceType"
      :label="$t('manual_balances_form.fields.balance_type')"
      outlined
    />

    <asset-select
      v-model="asset"
      :label="$t('common.asset')"
      :error-messages="errors['asset']"
      class="manual-balances-form__asset"
      outlined
      :rules="assetRules"
      :disabled="pending"
      @focus="delete errors['asset']"
    />
    <amount-input
      v-model="amount"
      :label="$t('common.amount')"
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
      :label="$t('common.location')"
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
import { get, set } from '@vueuse/core';
import { IVueI18n } from 'vue-i18n';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import BalanceTypeInput from '@/components/inputs/BalanceTypeInput.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import i18n from '@/i18n';
import { BalanceType, ManualBalance } from '@/services/balances/types';
import { deserializeApiErrorMessage } from '@/services/converters';
import { TradeLocation } from '@/services/history/types';
import { useManualBalancesStore } from '@/store/balances/manual';
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
  components: { BalanceTypeInput, LocationSelector, TagInput, AssetSelect },
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

    const input = (balance: ManualBalance) => {
      emit('input', balance);
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

    const save = async () => {
      set(pending, true);
      const balance: Omit<ManualBalance, 'id'> = {
        asset: get(asset),
        amount: bigNumberify(get(amount)),
        label: get(label),
        tags: get(tags),
        location: get(location),
        balanceType: get(balanceType)
      };

      const idVal = get(id);

      const status = await (get(edit) && idVal
        ? editManualBalance({ ...balance, id: idVal })
        : addManualBalance(balance));

      set(pending, false);

      if (status.success) {
        clear();
        return true;
      }

      if (status.message) {
        const errorMessages = deserializeApiErrorMessage(status.message);
        set(errors, (errorMessages?.balances[0] as any) ?? {});
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
            i18n
              .t('manual_balances_form.validation.label_exists', { label })
              .toString()
          ]
        });
      } else {
        const { label, ...data } = get(errors);
        set(errors, data);
      }
    });

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
