<script setup lang="ts">
import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { useFormStateWatcher } from '@/modules/core/common/use-form';
import { nullDefined, useRefPropVModel } from '@/modules/core/common/validation/model';
import { toMessages } from '@/modules/core/common/validation/validation';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const modelValue = defineModel<CounterpartyMapping>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { editMode = false } = defineProps<{
  editMode?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const asset = useRefPropVModel(modelValue, 'asset');
const counterpartySymbol = useRefPropVModel(modelValue, 'counterpartySymbol');
const counterparty = useRefPropVModel(modelValue, 'counterparty');
const counterpartyModel = nullDefined(counterparty);

const rules = {
  asset: {
    required: helpers.withMessage(t('asset_management.cex_mapping.form.asset_non_empty'), required),
  },
  counterparty: {
    required: helpers.withMessage(
      t('asset_management.counterparty_mapping.form.counterparty_non_empty'),
      required,
    ),
  },
  counterpartySymbol: {
    required: helpers.withMessage(
      t('asset_management.counterparty_mapping.form.counterparty_symbol_non_empty'),
      required,
    ),
  },
};

const states = {
  asset,
  counterparty,
  counterpartySymbol,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true, $externalResults: errors },
);

useFormStateWatcher(states, stateUpdated);

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <CounterpartyInput
      v-model="counterpartyModel"
      :label="t('common.counterparty')"
      :disabled="editMode"
      exclude-exchanges
      clearable
      :error-messages="toMessages(v$.counterparty)"
    />
    <RuiTextField
      v-model="counterpartySymbol"
      data-cy="counterpartySymbol"
      variant="outlined"
      color="primary"
      :disabled="editMode"
      clearable
      :label="t('asset_management.counterparty_mapping.counterparty_symbol')"
      :error-messages="toMessages(v$.counterpartySymbol)"
    />
    <AssetSelect
      v-model="asset"
      :label="t('asset_management.cex_mapping.recognized_as')"
      outlined
      :error-messages="toMessages(v$.asset)"
    />
  </div>
</template>
