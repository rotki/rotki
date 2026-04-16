<script setup lang="ts">
import HistoryEventsDecodingStatus from '@/modules/history/events/HistoryEventsDecodingStatus.vue';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';

interface Props {
  persistent?: boolean;
  refreshing: boolean;
}

interface Emits {
  'redecode-all-events': [];
  'reset-undecoded-transactions': [];
}

const modelValue = defineModel<boolean>({ required: true });

const {
  persistent = false,
  refreshing,
} = defineProps<Props>();

const emit = defineEmits<Emits>();

const { decodingStatus } = storeToRefs(useDecodingStatusStore());

function onRedecodeAllEvents(): void {
  emit('redecode-all-events');
}

function onResetUndecodedTransactions(): void {
  emit('reset-undecoded-transactions');
}

function closeDialog(): void {
  set(modelValue, false);
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="600"
    :persistent="persistent"
  >
    <HistoryEventsDecodingStatus
      v-if="modelValue"
      :refreshing="refreshing"
      :decoding-status="decodingStatus"
      @redecode-all-events="onRedecodeAllEvents()"
      @reset-undecoded-transactions="onResetUndecodedTransactions()"
    >
      <RuiButton
        variant="text"
        icon
        @click="closeDialog()"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </HistoryEventsDecodingStatus>
  </RuiDialog>
</template>
