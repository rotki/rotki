<script lang="ts" setup>
import type { EvmChainInfo } from '@/types/api/chains';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const props = defineProps<{
  item: EvmChainInfo;
  detecting: boolean;
  enabled: boolean;
  allowRedetect: boolean;
}>();

const emit = defineEmits<{
  toggle: [chain: string];
  detect: [chain: string];
}>();

const { useIsTaskRunning } = useTaskStore();
const { t } = useI18n({ useScope: 'global' });

const taskMeta = computed(() => ({
  chain: props.item.id,
}));

const isDetectingChain = useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS, taskMeta);
</script>

<template>
  <RuiCheckbox
    :model-value="enabled"
    :disabled="detecting"
    color="primary"
    size="sm"
    hide-details
    @click.prevent.stop="emit('toggle', item.id)"
  />
  <LocationIcon
    size="1.25"
    class="text-sm"
    :item="item.evmChainName"
    horizontal
  />
  <div class="grow" />
  <TransitionGroup
    enter-active-class="opacity-100"
    leave-active-class="opacity-0"
  >
    <RuiButton
      v-if="allowRedetect"
      variant="text"
      color="primary"
      class="flex !px-4 !py-2"
      size="sm"
      :loading="isDetectingChain"
      @click.prevent.stop="emit('detect', item.id)"
    >
      <div class="flex items-center gap-1.5">
        <RuiIcon
          name="lu-refresh-ccw"
          size="16"
        />
        {{ t('account_balances.detect_tokens.selection.redetect') }}
      </div>
    </RuiButton>
  </TransitionGroup>
</template>
