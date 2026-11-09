<script setup lang="ts">
interface LogEntry {
  message: string;
  timestamp: string;
  type: 'info' | 'success' | 'error';
}

const { logs } = defineProps<{
  logs: LogEntry[];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCard
    divide
    no-padding
  >
    <template #header>
      {{ t('trade.bridge.connection_logs') }}
    </template>
    <div class="max-h-64 overflow-y-auto divide-y divide-default text-xs">
      <div
        v-for="(log, index) in logs"
        :key="index"
        class="flex gap-3 px-4 py-2"
      >
        <span class="font-mono text-rui-text-disabled shrink-0">{{ log.timestamp }}</span>
        <span
          class="break-words min-w-0"
          :class="{
            'text-rui-text-secondary': log.type === 'info',
            'text-rui-success': log.type === 'success',
            'text-rui-error': log.type === 'error',
          }"
        >
          {{ log.message }}
        </span>
      </div>
    </div>
  </RuiCard>
</template>
