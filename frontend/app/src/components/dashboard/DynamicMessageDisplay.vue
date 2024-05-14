<script setup lang="ts">
import type { DashboardMessage } from '@/types/dynamic-messages';

const props = defineProps<{
  messages: DashboardMessage[];
}>();

const emit = defineEmits<{
  (e: 'dismiss'): void;
}>();

const { step, steps, onNavigate, onPause, onResume } = useRandomStepper(props.messages.length);

const activeItem = computed(() => props.messages[get(step) - 1]);
</script>

<template>
  <div
    class="px-4 py-2 text-body-1 text-rui-primary flex items-center justify-between border-b border-default w-full bg-white dark:bg-[#1E1E1E] gap-4"
  >
    <div
      class="flex-1 md:text-center"
      @mouseover="onPause()"
      @mouseleave="onResume()"
    >
      <FadeTransition>
        <div
          v-if="activeItem"
          :key="step"
        >
          {{ activeItem.message }}
          <div class="font-semibold inline">
            <template v-if="activeItem.messageHighlight">
              {{ activeItem.messageHighlight }}
            </template>

            <ExternalLink
              v-if="activeItem.action"
              color="primary"
              class="text-left md:text-center"
              :url="activeItem.action?.url"
            >
              {{ activeItem.action.text }}
            </ExternalLink>
          </div>
        </div>
      </FadeTransition>
    </div>

    <RuiFooterStepper
      v-if="steps > 1"
      class="ml-auto"
      :value="step"
      :pages="steps"
      variant="bullet"
      hide-buttons
      @input="onNavigate($event)"
    />

    <RuiButton
      variant="text"
      icon
      color="primary"
      size="sm"
      @click="emit('dismiss')"
    >
      <RuiIcon name="close-line" />
    </RuiButton>
  </div>
</template>
