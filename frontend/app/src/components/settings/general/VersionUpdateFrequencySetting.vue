<template>
  <v-row>
    <v-col class="grow">
      <settings-option
        #default="{ error, success, update }"
        setting="versionUpdateCheckFrequency"
        frontend-setting
        :transform="frequencyTransform"
        :error-message="
          tc('general_settings.validation.version_update_check_frequency.error')
        "
        @finished="resetVersionUpdateCheckFrequency"
      >
        <v-text-field
          v-model="versionUpdateCheckFrequency"
          outlined
          :disabled="!versionUpdateCheckEnabled"
          type="number"
          min="1"
          :max="maxVersionUpdateCheckFrequency"
          :label="tc('general_settings.labels.version_update_check')"
          persistent-hint
          :hint="tc('general_settings.version_update_check_hint')"
          :success-messages="success"
          :error-messages="
            error || v$.versionUpdateCheckFrequency.$errors.map(e => e.$message)
          "
          @change="update"
        />
      </settings-option>
    </v-col>
    <v-col class="shrink">
      <settings-option
        #default="{ update }"
        setting="versionUpdateCheckFrequency"
        frontend-setting
        :transform="switchTransform"
        @finished="resetVersionUpdateCheckFrequency"
      >
        <v-switch
          v-model="versionUpdateCheckEnabled"
          class="mt-3"
          :label="tc('general_settings.labels.version_update_check_enabled')"
          @change="callIfValid($event, update)"
        />
      </settings-option>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const versionUpdateCheckFrequency = ref<string>('');
const versionUpdateCheckEnabled = ref<boolean>(false);

const { versionUpdateCheckFrequency: existingFrequency } = storeToRefs(
  useFrontendSettingsStore()
);

const maxVersionUpdateCheckFrequency = Constraints.MAX_HOURS_DELAY;
const { tc } = useI18n();

const rules = {
  versionUpdateCheckFrequency: {
    required: helpers.withMessage(
      tc(
        'general_settings.validation.version_update_check_frequency.non_empty'
      ),
      required
    ),
    between: helpers.withMessage(
      tc(
        'general_settings.validation.version_update_check_frequency.invalid_frequency',
        0,
        {
          start: 1,
          end: maxVersionUpdateCheckFrequency
        }
      ),
      between(1, Constraints.MAX_HOURS_DELAY)
    )
  }
};

const v$ = useVuelidate(
  rules,
  { versionUpdateCheckFrequency },
  { $autoDirty: true }
);
const { callIfValid } = useValidation(v$);

const resetVersionUpdateCheckFrequency = () => {
  const frequency = get(existingFrequency);
  set(versionUpdateCheckEnabled, frequency > 0);
  set(
    versionUpdateCheckFrequency,
    get(versionUpdateCheckEnabled) ? frequency.toString() : ''
  );
};

const frequencyTransform = (value: string) => (value ? parseInt(value) : value);
const switchTransform = (value: boolean) => (value ? 24 : -1);

onMounted(() => {
  resetVersionUpdateCheckFrequency();
});
</script>
