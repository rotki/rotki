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
    <VAlert type="warning" text prominent class="pl-8">
      <div class="ml-4">
        <I18n path="docker_warning.title" tag="div">
          <BaseExternalLink
            :text="t('docker_warning.documentation')"
            :href="usageGuideUrl + '#docker'"
          />
        </I18n>
      </div>
    </VAlert>

    <VBtn class="mt-8" block depressed color="primary" @click="proceed()">
      {{ t('docker_warning.action') }}
    </VBtn>
  </div>
</template>
