<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { CexMapping } from '@/types/asset';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import ExchangeInput from '@/components/inputs/ExchangeInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { nullDefined, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<CexMapping>({ required: true });
const forAllExchanges = defineModel<boolean>('forAllExchanges', { required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

withDefaults(
  defineProps<{
    editMode?: boolean;
  }>(),
  {
    editMode: false,
  },
);

const { t } = useI18n({ useScope: 'global' });

const asset = useRefPropVModel(modelValue, 'asset');
const locationSymbol = useRefPropVModel(modelValue, 'locationSymbol');
const location = useRefPropVModel(modelValue, 'location');
const locationModel = nullDefined(location);

function checkPassedForm() {
  const data = get(modelValue);
  if (data) {
    set(forAllExchanges, !data.location);
  }
  else {
    set(forAllExchanges, false);
  }
}

const rules = {
  asset: {
    required: helpers.withMessage(t('asset_management.cex_mapping.form.asset_non_empty'), required),
  },
  location: {
    required: helpers.withMessage(
      t('asset_management.cex_mapping.form.location_non_empty'),
      requiredIf(logicNot(forAllExchanges)),
    ),
  },
  locationSymbol: {
    required: helpers.withMessage(
      t('asset_management.cex_mapping.form.location_symbol_non_empty'),
      required,
    ),
  },
};

const states = {
  asset,
  location,
  locationSymbol,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true, $externalResults: errors },
);

useFormStateWatcher(states, stateUpdated);

onBeforeMount(() => {
  checkPassedForm();
});

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <RuiSwitch
      v-model="forAllExchanges"
      :disabled="editMode"
      color="primary"
    >
      {{ t('asset_management.cex_mapping.save_for_all') }}
    </RuiSwitch>
    <ExchangeInput
      v-model="locationModel"
      :label="t('asset_management.cex_mapping.exchange')"
      :disabled="editMode || forAllExchanges"
      clearable
      :error-messages="toMessages(v$.location)"
    />
    <RuiTextField
      v-model="locationSymbol"
      data-cy="locationSymbol"
      variant="outlined"
      color="primary"
      :disabled="editMode"
      clearable
      :label="t('asset_management.cex_mapping.location_symbol')"
      :error-messages="toMessages(v$.locationSymbol)"
    />
    <AssetSelect
      v-model="asset"
      :label="t('asset_management.cex_mapping.recognized_as')"
      outlined
      :error-messages="toMessages(v$.asset)"
    />
  </div>
</template>
