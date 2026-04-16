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
      class="!bg-rui-grey-200 dark:!bg-rui-grey-900 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800"
      size="sm"
      color="primary"
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
