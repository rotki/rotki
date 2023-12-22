<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

const { dockerRiskAccepted } = storeToRefs(useMainStore());
const { t } = useI18n();
const { usageGuideSection } = externalLinks;

const proceed = () => {
  set(dockerRiskAccepted, true);
};
</script>

<template>
  <div class="max-w-[41.25rem] mx-auto">
    <RuiAlert type="warning">
      <i18n path="docker_warning.title">
        <ExternalLink
          :text="t('docker_warning.documentation')"
          :url="usageGuideSection.dockerWarning"
          color="warning"
        />
      </i18n>

      <RuiButton class="mt-4" size="sm" color="primary" @click="proceed()">
        {{ t('docker_warning.action') }}
      </RuiButton>
    </RuiAlert>
  </div>
</template>
