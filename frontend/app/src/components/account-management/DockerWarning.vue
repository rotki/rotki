<script setup lang="ts">
const { dockerRiskAccepted } = storeToRefs(useMainStore());
const { t } = useI18n();
const { usageGuideUrl } = useInterop();

const proceed = () => {
  set(dockerRiskAccepted, true);
};
</script>

<template>
  <div class="pa-6 pb-2">
    <v-alert type="warning" text prominent class="pl-8">
      <div class="ml-4">
        <i18n path="docker_warning.title" tag="div">
          <base-external-link
            :text="t('docker_warning.documentation')"
            :href="usageGuideUrl + '#docker'"
          />
        </i18n>
      </div>
    </v-alert>

    <v-btn class="mt-8" block depressed color="primary" @click="proceed()">
      {{ t('docker_warning.action') }}
    </v-btn>
  </div>
</template>
