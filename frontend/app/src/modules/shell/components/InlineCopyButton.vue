<script lang="ts" setup>
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';

const { text, size } = defineProps<{
  text: string;
  size: string | number;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <CopyTooltip :value="text">
    <RuiButton
      variant="text"
      icon
      class="text-rui-text-secondary! hover:text-rui-primary! hover:bg-rui-grey-100! dark:hover:bg-rui-grey-800!"
      size="sm"
      color="primary"
      :aria-label="t('common.actions.copy_to_clipboard')"
    >
      <RuiIcon
        name="lu-copy"
        :size="size"
      />
    </RuiButton>
    <template #label>
      {{ t('common.actions.copy_to_clipboard') }}
    </template>
  </CopyTooltip>
</template>
