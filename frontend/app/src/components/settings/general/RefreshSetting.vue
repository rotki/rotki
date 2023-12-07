<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/data/constraints';

const refreshPeriod = ref<string>('');
const refreshEnabled = ref<boolean>(false);

const minRefreshPeriod = 30;
const maxRefreshPeriod = Constraints.MAX_MINUTES_DELAY;

const { t } = useI18n();

const rules = {
  refreshPeriod: {
    required: helpers.withMessage(
      t('frontend_settings.validation.refresh_period.non_empty'),
      required
    ),
    between: helpers.withMessage(
      t('frontend_settings.validation.refresh_period.invalid_period', {
        start: minRefreshPeriod,
        end: maxRefreshPeriod
      }),
      between(minRefreshPeriod, maxRefreshPeriod)
    )
  }
};

const v$ = useVuelidate(rules, { refreshPeriod }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const { refreshPeriod: currentPeriod } = storeToRefs(
  useFrontendSettingsStore()
);

const resetRefreshPeriod = () => {
  const period = get(currentPeriod);
  set(refreshEnabled, period > 0);
  set(refreshPeriod, get(refreshEnabled) ? period.toString() : '');
};

const transform = (value: string) => (value ? Number.parseInt(value) : value);
const transformSwitch = (value: boolean) => (value ? 30 : -1);

onMounted(() => {
  resetRefreshPeriod();
});
</script>

<template>
  <div class="mt-8">
    <div class="text-h6">
      {{ t('frontend_settings.subtitle.refresh') }}
    </div>
    <div class="flex gap-6 mt-1">
      <div class="grow">
        <SettingsOption
          #default="{ error, success, update }"
          setting="refreshPeriod"
          frontend-setting
          :transform="transform"
          :error-message="
            t('frontend_settings.validation.refresh_period.error')
          "
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
            :label="t('frontend_settings.label.refresh')"
            :hint="t('frontend_settings.hint.refresh')"
            :success-messages="success"
            :error-messages="
              error || v$.refreshPeriod.$errors.map(e => e.$message)
            "
            @input="callIfValid($event, update)"
          />
        </SettingsOption>
      </div>
      <SettingsOption
        #default="{ update }"
        setting="refreshPeriod"
        frontend-setting
        :transform="transformSwitch"
        :error-message="t('frontend_settings.validation.refresh_period.error')"
        @finished="resetRefreshPeriod()"
      >
        <VSwitch
          v-model="refreshEnabled"
          class="mt-3"
          :label="t('frontend_settings.label.refresh_enabled')"
          @change="update($event)"
        />
      </SettingsOption>
    </div>
  </div>
</template>
