<script setup lang="ts">
import { externalLinks } from '@shared/external-links';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

function goBack(): void {
  router.back();
}
</script>

<template>
  <div class="flex items-center justify-center h-full w-full min-h-[300px] p-6">
    <div class="flex flex-col items-center text-center max-w-md">
      <RuiIcon
        name="lu-circle-alert"
        color="error"
        size="64"
        class="mb-4"
      />
      <h3 class="text-h6 mb-2">
        {{ t('premium_loading_failed.title') }}
      </h3>
      <p class="text-body-2 text-rui-text-secondary mb-4">
        {{ t('premium_loading_failed.description') }}
      </p>
      <div class="flex flex-col gap-2 text-body-2 text-rui-text-secondary mb-6">
        <span>{{ t('premium_loading_failed.try_again') }}</span>
        <span>{{ t('premium_loading_failed.open_issue') }}</span>
      </div>
      <div class="flex gap-3">
        <RuiButton
          color="primary"
          @click="goBack()"
        >
          <template #prepend>
            <RuiIcon name="lu-arrow-left" />
          </template>
          {{ t('common.actions.back') }}
        </RuiButton>
        <RuiButton
          variant="outlined"
          color="primary"
          tag="a"
          :href="externalLinks.githubNewBugReport"
          target="_blank"
        >
          <template #prepend>
            <RuiIcon name="lu-external-link" />
          </template>
          {{ t('help_sidebar.report_issue.title') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
