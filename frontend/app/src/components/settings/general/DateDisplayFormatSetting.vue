<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { displayDateFormatter } from '@/data/date_formatter';
import { Defaults } from '@/data/defaults';

const dateDisplayFormat = ref<string>('');
const formatHelp = ref<boolean>(false);
const now = new Date();
const defaultDateDisplayFormat = Defaults.DEFAULT_DATE_DISPLAY_FORMAT;

const containsValidDirectives = (v: string) =>
  displayDateFormatter.containsValidDirectives(v);

const { t } = useI18n();

const rules = {
  dateDisplayFormat: {
    required: helpers.withMessage(
      t('general_settings.date_display.validation.empty'),
      required
    ),
    containsValidDirectives: helpers.withMessage(
      t('general_settings.date_display.validation.invalid'),
      containsValidDirectives
    )
  }
};

const v$ = useVuelidate(rules, { dateDisplayFormat }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { dateDisplayFormat: format } = storeToRefs(useGeneralSettingsStore());

const dateDisplayFormatExample = computed<string>(() =>
  displayDateFormatter.format(now, get(dateDisplayFormat))
);

const resetDateDisplayFormat = () => {
  set(dateDisplayFormat, get(format));
};

const successMessage = (dateFormat: string) =>
  t('general_settings.validation.date_display_format.success', {
    dateFormat
  });

onMounted(() => {
  resetDateDisplayFormat();
});
</script>

<template>
  <div>
    <DateFormatHelp v-model="formatHelp" />
    <SettingsOption
      #default="{ error, success, update }"
      setting="dateDisplayFormat"
      :error-message="
        t('general_settings.validation.date_display_format.error')
      "
      :success-message="successMessage"
      @finished="resetDateDisplayFormat()"
    >
      <VTextField
        v-model="dateDisplayFormat"
        outlined
        class="general-settings__fields__date-display-format"
        :label="t('general_settings.labels.date_display_format')"
        type="text"
        :success-messages="success"
        :error-messages="
          error || v$.dateDisplayFormat.$errors.map(e => e.$message)
        "
        :hint="
          t('general_settings.date_display_format_hint', {
            format: dateDisplayFormatExample
          })
        "
        persistent-hint
        @change="callIfValid($event, update)"
      >
        <template #append>
          <RuiButton size="sm" icon variant="text" @click="formatHelp = true">
            <VIcon small> mdi-information </VIcon>
          </RuiButton>
        </template>
        <template #append-outer>
          <VTooltip top open-delay="400">
            <template #activator="{ on, attrs }">
              <RuiButton
                class="general-settings__date-restore mt-n2"
                icon
                variant="text"
                v-bind="attrs"
                @click="update(defaultDateDisplayFormat)"
                v-on="on"
              >
                <VIcon> mdi-backup-restore </VIcon>
              </RuiButton>
            </template>
            <span>{{ t('general_settings.date_display_tooltip') }}</span>
          </VTooltip>
        </template>
      </VTextField>
    </SettingsOption>
  </div>
</template>
