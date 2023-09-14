<script setup lang="ts">
const { dockerRiskAccepted } = storeToRefs(useMainStore());
const { t } = useI18n();
const { usageGuideUrl } = useInterop();

const proceed = () => {
  set(dockerRiskAccepted, true);
};
</script>

<template>
  <div class="max-w-[41.25rem] mx-auto">
    <RuiAlert type="warning">
      <i18n path="docker_warning.title" tag="div">
        <BaseExternalLink
          :text="t('docker_warning.documentation')"
          :href="usageGuideUrl + '#docker'"
        />
      </i18n>

      <RuiButton class="mt-4" depressed color="primary" @click="proceed()">
        {{ t('docker_warning.action') }}
      </RuiButton>
    </RuiAlert>
  </div>
</template>
