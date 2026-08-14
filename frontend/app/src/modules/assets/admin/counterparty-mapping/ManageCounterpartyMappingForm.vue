<script setup lang="ts">
import type { ZodType } from 'zod';
import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { counterpartyMappingSchema } from '@/modules/assets/admin/counterparty-mapping/counterparty-mapping-form';
import { useModelForm } from '@/modules/core/form/use-model-form';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const modelValue = defineModel<CounterpartyMapping>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { editMode = false } = defineProps<{
  editMode?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => counterpartyMappingSchema({
  asset: t('asset_management.cex_mapping.form.asset_non_empty'),
  counterparty: t('asset_management.counterparty_mapping.form.counterparty_non_empty'),
  counterpartySymbol: t('asset_management.counterparty_mapping.form.counterparty_symbol_non_empty'),
}));

const form = useModelForm<CounterpartyMapping>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
});

/**
 * The input clears to `undefined`, which used to be written back as `null` into a field the payload
 * types as a string. Nothing downstream ever saw it, because save is gated on a rule a cleared field
 * fails either way, so it empties instead of lying about its type.
 */
const counterpartyModel = computed<string | undefined>({
  get: () => form.state.counterparty,
  set: (value?: string) => {
    form.state.counterparty = value ?? '';
    form.touch('counterparty');
  },
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <CounterpartyInput
      v-model="counterpartyModel"
      data-testid="counterparty"
      :label="t('common.counterparty')"
      :disabled="editMode"
      exclude-exchanges
      clearable
      :error-messages="form.errors('counterparty')"
    />
    <RuiTextField
      v-model="form.state.counterpartySymbol"
      data-testid="counterparty-symbol"
      variant="outlined"
      color="primary"
      :disabled="editMode"
      clearable
      :label="t('asset_management.counterparty_mapping.counterparty_symbol')"
      :error-messages="form.errors('counterpartySymbol')"
      @update:model-value="form.touch('counterpartySymbol')"
    />
    <AssetSelect
      v-model="form.state.asset"
      data-testid="counterparty-asset"
      :label="t('asset_management.cex_mapping.recognized_as')"
      outlined
      :error-messages="form.errors('asset')"
      @update:model-value="form.touch('asset')"
    />
  </div>
</template>
