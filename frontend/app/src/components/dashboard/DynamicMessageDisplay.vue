<script setup lang="ts">
import { type DashboardMessage } from '@/types/dynamic-messages';

defineProps<{
  message: DashboardMessage;
}>();

const emit = defineEmits<{
  (e: 'dismiss'): void;
}>();
</script>

<template>
  <div
    class="h-11 px-4 py-2 text-body-1 text-rui-primary flex items-center border-b border-default gap-1 w-full bg-white dark:bg-[#1E1E1E] justify-center"
  >
    {{ message.message }}
    <div class="font-semibold">
      <template v-if="message.messageHighlight">
        {{ message.messageHighlight }}
      </template>

      <ExternalLink
        v-if="message.action"
        :url="message.action?.url"
        class="underline"
      >
        {{ message.action.text }}
      </ExternalLink>
    </div>
    <RuiButton
      variant="text"
      icon
      color="primary"
      class="absolute right-0 mr-3"
      size="sm"
      @click="emit('dismiss')"
    >
      <RuiIcon name="close-line" />
    </RuiButton>
  </div>
</template>
