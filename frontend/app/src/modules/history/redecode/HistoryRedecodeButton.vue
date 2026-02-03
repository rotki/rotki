<script setup lang="ts">
import { checkIfDevelopment } from '@shared/utils';
import HistoryRedecodeSelection from '@/modules/history/redecode/HistoryRedecodeSelection.vue';

defineProps<{
  processing: boolean;
}>();

const emit = defineEmits<{ redecode: [payload: 'all' | 'page' | string[]] }>();

const { t } = useI18n({ useScope: 'global' });
const isDemoMode = import.meta.env.VITE_DEMO_MODE !== undefined;
const isDevelopment = checkIfDevelopment();
</script>

<template>
  <RuiButtonGroup
    color="primary"
    :disabled="processing"
    :class="{
      '!divide-rui-grey-200 dark:!divide-rui-grey-800': processing,
    }"
  >
    <RuiButton
      class="!py-2"
      @click="emit('redecode', 'all')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-refresh-cw"
          size="16"
        />
      </template>
      {{ t('transactions.events_decoding.redecode') }}
    </RuiButton>

    <HistoryRedecodeSelection
      :loading="processing"
      :disabled="processing"
      :show-redecode-page="isDevelopment && !isDemoMode"
      @redecode="emit('redecode', $event)"
    />
  </RuiButtonGroup>
</template>
