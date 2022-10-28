<template>
  <div class="mt-12">
    <div class="text-h6">
      {{ tc('frontend_settings.subtitle.refresh') }}
    </div>
    <v-row class="mt-1">
      <v-col class="grow">
        <settings-option
          #default="{ error, success, update }"
          setting="refreshPeriod"
          frontend-setting
          :transform="transform"
          :error-message="
            tc('frontend_settings.validation.refresh_period.error')
          "
          @finished="resetRefreshPeriod"
        >
          <v-text-field
            v-model="refreshPeriod"
            outlined
            :disabled="!refreshEnabled"
            type="number"
            :min="minRefreshPeriod"
            :max="maxRefreshPeriod"
            :label="tc('frontend_settings.label.refresh')"
            persistent-hint
            :hint="tc('frontend_settings.hint.refresh')"
            :success-messages="success"
            :error-messages="
              error || v$.refreshPeriod.$errors.map(e => e.$message)
            "
            @change="callIfValid($event, update)"
          />
        </settings-option>
      </v-col>
      <v-col class="shrink">
        <settings-option
          #default="{ update }"
          setting="refreshPeriod"
          frontend-setting
          :transform="transformSwitch"
          :error-message="
            tc('frontend_settings.validation.refresh_period.error')
          "
          @finished="resetRefreshPeriod"
        >
          <v-switch
            v-model="refreshEnabled"
            class="mt-3"
            :label="tc('frontend_settings.label.refresh_enabled')"
            @change="update"
          />
        </settings-option>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const refreshPeriod = ref<string>('');
const refreshEnabled = ref<boolean>(false);

const minRefreshPeriod = 30;
const maxRefreshPeriod = Constraints.MAX_MINUTES_DELAY;

const { tc } = useI18n();

const rules = {
  refreshPeriod: {
    required: helpers.withMessage(
      tc('frontend_settings.validation.refresh_period.non_empty'),
      required
    ),
    between: helpers.withMessage(
      tc('frontend_settings.validation.refresh_period.invalid_period', 0, {
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

const transform = (value: string) => (value ? parseInt(value) : value);
const transformSwitch = (value: boolean) => (value ? 30 : -1);

onMounted(() => {
  resetRefreshPeriod();
});
</script>
