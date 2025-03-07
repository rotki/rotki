<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { useMainStore } from '@/store/main';
import { externalLinks } from '@shared/external-links';

const { dockerRiskAccepted } = storeToRefs(useMainStore());
const { t } = useI18n();
const { usageGuideSection } = externalLinks;

function proceed() {
  set(dockerRiskAccepted, true);
}
</script>

<template>
  <div class="max-w-[27.5rem] mx-auto">
    <RuiAlert type="warning">
      <i18n-t keypath="docker_warning.title">
        <ExternalLink
          :text="t('docker_warning.documentation')"
          :url="usageGuideSection.dockerWarning"
          color="warning"
        />
      </i18n-t>

      <RuiButton
        class="mt-4"
        size="sm"
        color="secondary"
        @click="proceed()"
      >
        {{ t('docker_warning.action') }}
      </RuiButton>
    </RuiAlert>
  </div>
</template>
