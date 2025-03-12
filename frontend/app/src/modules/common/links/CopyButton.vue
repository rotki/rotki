<script lang="ts" setup>
defineProps<{
  text: string;
  size: string | number;
}>();

const { t } = useI18n({ useScope: 'global' });
const { copy } = useClipboard();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="600"
  >
    <template #activator>
      <RuiButton
        variant="text"
        icon
        class="!bg-rui-grey-200 dark:!bg-rui-grey-900 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800"
        size="sm"
        color="primary"
        @click="copy(text)"
      >
        <RuiIcon
          name="lu-copy"
          :size="size"
        />
      </RuiButton>
    </template>

    {{ t('common.actions.copy_to_clipboard') }}
  </RuiTooltip>
</template>
