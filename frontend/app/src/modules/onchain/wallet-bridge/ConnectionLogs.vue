<script setup lang="ts">
interface LogEntry {
  message: string;
  timestamp: string;
  type: 'info' | 'success' | 'error';
}

const props = defineProps<{
  logs: LogEntry[];
}>();

const { t } = useI18n({ useScope: 'global' });

const { logs } = toRefs(props);
</script>

<template>
  <div class="mt-4 pt-4 border-t border-default">
    <h5 class="font-bold mb-3">
      {{ t('trade.bridge.connection_logs') }}
    </h5>
    <div class="border border-default rounded-md p-4 max-h-[300px] overflow-y-auto bg-rui-grey-50 dark:bg-rui-grey-900">
      <p
        v-for="(log, index) in logs"
        :key="index"
        class="mb-2 pb-2 border-b border-default font-mono last:mb-0 last:pb-0 last:border-0 text-sm break-words"
        :class="{
          'text-rui-primary': log.type === 'info',
          'text-rui-success': log.type === 'success',
          'text-rui-error': log.type === 'error',
        }"
      >
        <span class="text-gray-500 mr-1">{{ log.timestamp }}</span>
        {{ log.message }}
      </p>
    </div>
  </div>
</template>
