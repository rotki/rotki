<template>
  <v-row>
    <v-col class="grow">
      <settings-option
        #default="{ error, success, update }"
        setting="versionUpdateCheckFrequency"
        frontend-setting
        :transform="value => (value ? parseInt(value) : value)"
        :error-message="
          $t('general_settings.validation.version_update_check_frequency.error')
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
          :label="$t('general_settings.labels.version_update_check')"
          persistent-hint
          :hint="$t('general_settings.version_update_check_hint')"
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
        :transform="value => (value ? 24 : -1)"
        @finished="resetVersionUpdateCheckFrequency"
      >
        <v-switch
          v-model="versionUpdateCheckEnabled"
          class="mt-3"
          :label="$t('general_settings.labels.version_update_check_enabled')"
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
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import i18n from '@/i18n';
import { useFrontendSettingsStore } from '@/store/settings';

const versionUpdateCheckFrequency = ref<string>('');
const versionUpdateCheckEnabled = ref<boolean>(false);

const { versionUpdateCheckFrequency: existingFrequency } = storeToRefs(
  useFrontendSettingsStore()
);

const maxVersionUpdateCheckFrequency = Constraints.MAX_HOURS_DELAY;

const rules = {
  versionUpdateCheckFrequency: {
    required: helpers.withMessage(
      i18n
        .t(
          'general_settings.validation.version_update_check_frequency.non_empty'
        )
        .toString(),
      required
    ),
    between: helpers.withMessage(
      i18n
        .t(
          'general_settings.validation.version_update_check_frequency.invalid_frequency',
          {
            start: 1,
            end: maxVersionUpdateCheckFrequency
          }
        )
        .toString(),
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

onMounted(() => {
  resetVersionUpdateCheckFrequency();
});
</script>
