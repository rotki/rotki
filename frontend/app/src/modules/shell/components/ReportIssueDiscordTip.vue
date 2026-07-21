<script setup lang="ts">
const emit = defineEmits<{
  'open-discord': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-start gap-3 p-3 bg-rui-grey-100 dark:bg-rui-grey-800 rounded">
    <RuiIcon
      name="lu-discord"
      class="text-rui-text-secondary shrink-0 mt-0.5"
    />
    <div class="flex flex-col gap-1">
      <span class="text-sm">
        {{ t('help_sidebar.report_issue.dialog.tips.discord.title') }}
      </span>
      <i18n-t
        keypath="help_sidebar.report_issue.dialog.tips.discord.description"
        tag="span"
        class="text-xs text-rui-text-secondary"
        scope="global"
      >
        <template #channel>
          <span class="font-mono">{{ t('help_sidebar.report_issue.dialog.tips.discord.channel') }}</span>
        </template>
      </i18n-t>
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        class="self-start -ml-1.5 !py-0"
        @click="emit('open-discord')"
      >
        {{ t('help_sidebar.report_issue.dialog.tips.discord.action') }}
      </RuiButton>
    </div>
  </div>
</template>
