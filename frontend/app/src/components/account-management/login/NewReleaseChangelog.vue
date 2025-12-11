<script setup lang="ts">
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { useUpdateMessage } from '@/composables/update-message';

const { t } = useI18n({ useScope: 'global' });

const { link, version } = useUpdateMessage();
</script>

<template>
  <div class="flex flex-col items-start gap-4 w-full p-6 bg-[rgba(78,91,166,0.04)]">
    <div class="bg-white rounded-[0.625rem] p-3">
      <RuiIcon
        color="primary"
        name="lu-circle-check"
      />
    </div>
    <div class="text-h6 text-rui-text">
      {{ t('welcome.update.title') }}
    </div>
    <div class="text-body-1 text-rui-text-secondary">
      {{ t('welcome.update.text', { version }) }}
    </div>

    <ExternalLink
      :url="link"
      custom
    >
      <RuiButton color="primary">
        {{ t('welcome.update.learn_more') }}
      </RuiButton>
    </ExternalLink>
  </div>
</template>
