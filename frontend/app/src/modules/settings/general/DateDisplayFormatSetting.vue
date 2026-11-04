<script setup lang="ts">
import type { ZodType } from 'zod';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { Defaults } from '@/modules/core/common/defaults';
import DateFormatHelp from '@/modules/settings/controls/DateFormatHelp.vue';
import { SETTING_FIELD } from '@/modules/settings/controls/setting-field-schemas';
import { useSettingField } from '@/modules/settings/controls/use-setting-field';
import { dateFormatSchema } from '@/modules/settings/general/date-format-schema';
import SettingResetConfirmButton from '@/modules/settings/SettingResetConfirmButton.vue';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import { useSettingWriteFeedback } from '@/modules/settings/use-setting-write-feedback';

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, flush, model, success: writeSuccess } = useSettingModel('dateDisplayFormat', { debounce: 1500 });
const { clearAll, error, success } = useSettingWriteFeedback(
  { error: writeError, model, success: writeSuccess },
  () => t('general_settings.validation.date_display_format.success', { dateFormat: get(model) }),
  { errorPrefix: () => t('general_settings.validation.date_display_format.error') },
);

const formatHelp = ref<boolean>(false);
const now = new Date();
const defaultDateDisplayFormat = Defaults.DEFAULT_DATE_DISPLAY_FORMAT;

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

const dateDisplayFormatExample = computed<string>(() => displayDateFormatter.format(now, form.state.value));

async function reset(): Promise<void> {
  form.state.value = defaultDateDisplayFormat;
  set(model, defaultDateDisplayFormat);
  await flush();
}
</script>

<template>
  <div class="mb-6">
    <DateFormatHelp v-model="formatHelp" />
    <div class="flex items-start w-full">
      <RuiTextField
        v-model="form.state.value"
        color="primary"
        data-testid="date-display-format-input"
        class="grow"
        :label="t('general_settings.labels.date_display_format')"
        type="text"
        :success-messages="success"
        :error-messages="error || form.errors(SETTING_FIELD)"
        :hint="
          t('general_settings.date_display_format_hint', {
            format: dateDisplayFormatExample,
          })
        "
        @update:model-value="onInput($event)"
      >
        <template #append>
          <RuiButton
            size="sm"
            variant="text"
            icon
            @click="formatHelp = true"
          >
            <RuiIcon name="lu-info" />
          </RuiButton>
        </template>
      </RuiTextField>
      <SettingResetConfirmButton
        :tooltip="t('general_settings.date_display_tooltip')"
        labelled
        @confirm="reset()"
      />
    </div>
  </div>
</template>
