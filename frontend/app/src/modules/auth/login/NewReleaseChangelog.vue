<script setup lang="ts">
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import { useUpdateMessage } from '@/modules/core/messaging/use-update-message';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { t } = useI18n({ useScope: 'global' });

const { link, version } = useUpdateMessage();
</script>

<template>
  <div
    class="flex flex-col items-start gap-4 w-full p-6 rounded-lg bg-rui-primary/5"
    data-testid="new-release-changelog"
  >
    <div class="bg-white dark:bg-rui-grey-800 rounded-lg p-3">
      <RuiIcon
        color="primary"
        name="lu-sparkles"
      />
    </div>
    <div class="flex flex-col gap-2">
      <h3 class="text-h6 text-rui-text">
        {{ t('welcome.update.title', { version }) }}
      </h3>
      <p class="text-body-1 text-rui-text-secondary">
        {{ t('welcome.update.text', { version }) }}
      </p>
    </div>

    <ExternalLink
      :url="link"
      custom
    >
      <RuiButton color="primary">
        {{ t('welcome.update.learn_more') }}
        <template #append>
          <RuiIcon
            name="lu-external-link"
            size="16"
          />
        </template>
      </RuiButton>
    </ExternalLink>
  </div>
</template>
