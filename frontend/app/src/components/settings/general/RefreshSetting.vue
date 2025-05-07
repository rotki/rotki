<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';

const refreshPeriod = ref<string>('');
const refreshEnabled = ref<boolean>(false);

const minRefreshPeriod = 30;
const maxRefreshPeriod = Constraints.MAX_MINUTES_DELAY;

const { t } = useI18n({ useScope: 'global' });

const rules = {
  refreshPeriod: {
    between: helpers.withMessage(
      t('frontend_settings.refresh_balance.validation.invalid_period', {
        end: maxRefreshPeriod,
        start: minRefreshPeriod,
      }),
      between(minRefreshPeriod, maxRefreshPeriod),
    ),
    required: helpers.withMessage(t('frontend_settings.refresh_balance.validation.non_empty'), required),
  },
};

const v$ = useVuelidate(rules, { refreshPeriod }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { refreshPeriod: currentPeriod } = storeToRefs(useFrontendSettingsStore());

function resetRefreshPeriod() {
  const period = get(currentPeriod);
  set(refreshEnabled, period > 0);
  set(refreshPeriod, get(refreshEnabled) ? period.toString() : '');
}

const transform = (value: string) => (value ? Number.parseInt(value) : value);
const transformSwitch = (value: boolean) => (value ? 30 : -1);

onMounted(() => {
  resetRefreshPeriod();
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('frontend_settings.refresh_balance.title') }}
    </template>
    <SettingsOption
      #default="{ updateImmediate }"
      setting="refreshPeriod"
      frontend-setting
      :transform="transformSwitch"
      :error-message="t('frontend_settings.refresh_balance.validation.error')"
      @finished="resetRefreshPeriod()"
    >
      <RuiSwitch
        v-model="refreshEnabled"
        :label="t('frontend_settings.refresh_balance.label')"
        color="primary"
        @update:model-value="updateImmediate($event)"
      />
    </SettingsOption>

    <SettingsOption
      #default="{ error, success, update }"
      setting="refreshPeriod"
      frontend-setting
      :transform="transform"
      :error-message="t('frontend_settings.refresh_balance.validation.error')"
      @finished="resetRefreshPeriod()"
    >
      <RuiTextField
        v-model="refreshPeriod"
        variant="outlined"
        color="primary"
        :disabled="!refreshEnabled"
        type="number"
        :min="minRefreshPeriod"
        :max="maxRefreshPeriod"
        :label="t('frontend_settings.refresh_balance.period_label')"
        :success-messages="success"
        :error-messages="refreshEnabled ? (error || toMessages(v$.refreshPeriod)) : []"
        @update:model-value="callIfValid($event, update)"
      />
    </SettingsOption>
  </SettingsItem>
</template>
