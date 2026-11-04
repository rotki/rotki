<script setup lang="ts">
import type { ZodType } from 'zod';
import { SETTING_FIELD } from '@/modules/settings/controls/setting-field-schemas';
import { useSettingField } from '@/modules/settings/controls/use-setting-field';
import { dateFormatSchema } from '@/modules/settings/general/date-format-schema';
import DateInputFormatSelector from '@/modules/settings/general/DateInputFormatSelector.vue';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import { useSettingWriteFeedback } from '@/modules/settings/use-setting-write-feedback';

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, model, success: writeSuccess } = useSettingModel('dateInputFormat', { debounce: 0 });
const { clearAll, error, success } = useSettingWriteFeedback(
  { error: writeError, model, success: writeSuccess },
  () => t('general_settings.validation.date_input_format.success', { dateFormat: get(model) }),
  { errorPrefix: () => t('general_settings.validation.date_input_format.error') },
);

const schema = computed<ZodType>(() => dateFormatSchema({
  empty: t('general_settings.date_display.validation.empty'),
  invalid: t('general_settings.date_display.validation.invalid'),
}));

const { form, onInput } = useSettingField({
  fromField: (field: string): string => field,
  model,
  onEdit: clearAll,
  schema,
  toField: (value: string): string => value,
});
</script>

<template>
  <DateInputFormatSelector
    v-model="form.state.value"
    data-testid="date-input-format-input"
    :label="t('general_settings.labels.date_input_format')"
    :success-messages="success ? [success] : []"
    :error-messages="error ? [error] : form.errors(SETTING_FIELD)"
    @update:model-value="onInput($event)"
  />
</template>
