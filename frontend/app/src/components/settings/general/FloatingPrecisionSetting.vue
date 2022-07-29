<template>
  <settings-option
    #default="{ error, success, update }"
    setting="uiFloatingPrecision"
    :transform="value => (value ? parseInt(value) : value)"
    :error-message="
      precision =>
        $tc('general_settings.validation.floating_precision.error', 0, {
          precision
        })
    "
    :success-message="
      precision =>
        $tc('general_settings.validation.floating_precision.success', 0, {
          precision
        })
    "
    @finished="resetFloatingPrecision"
  >
    <v-text-field
      v-model="floatingPrecision"
      outlined
      min="1"
      :max="maxFloatingPrecision"
      class="general-settings__fields__floating-precision"
      :label="$t('general_settings.amount.labels.floating_precision')"
      type="number"
      :success-messages="success"
      :error-messages="
        error || v$.floatingPrecision.$errors.map(e => e.$message)
      "
      @change="callIfValid($event, update)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';
import { useValidation } from '@/composables/validation';
import i18n from '@/i18n';

const floatingPrecision = ref<string>('0');
const maxFloatingPrecision = 8;
const rules = {
  floatingPrecision: {
    required: helpers.withMessage(
      i18n
        .t('general_settings.validation.floating_precision.non_empty')
        .toString(),
      required
    )
  }
};

const { generalSettings } = useSettings();
const v$ = useVuelidate(rules, { floatingPrecision }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const resetFloatingPrecision = () => {
  const settings = get(generalSettings);
  set(floatingPrecision, settings.uiFloatingPrecision.toString());
};

onMounted(() => {
  resetFloatingPrecision();
});
</script>
