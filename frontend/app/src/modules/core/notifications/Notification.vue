<script setup lang="ts">
import { type NotificationData, Severity } from '@rotki/common';
import { useNotificationCard } from '@/modules/core/notifications/use-notification-card';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { notification, popup = false } = defineProps<{
  notification: NotificationData;
  popup?: boolean;
}>();

const emit = defineEmits<{
  dismiss: [id: number];
}>();

const { t } = useI18n({ useScope: 'global' });

const message = useTemplateRef<HTMLDivElement>('message');
const { height } = useElementSize(message);

function dismiss(id: number): void {
  emit('dismiss', id);
}

const {
  actions,
  buttonClicked,
  circleBgClass,
  colorBgClass,
  copy,
  doAction,
  expandButtonClass,
  expanded,
  getIcon,
  icon,
  messageClicked,
  messageWrapperStyle,
  showExpandArrow,
  timestamp,
} = useNotificationCard(() => notification, { dismiss, height });
</script>

<template>
  <RuiCard
    :class="[
      colorBgClass,
      {
        'rounded-none!': popup,
      },
    ]"
    class="p-2! pb-1.5! max-w-[400px]"
    no-padding
    :variant="popup ? 'flat' : 'outlined'"
    data-id="notification"
  >
    <div class="flex pb-1 items-center overflow-hidden">
      <div
        class="mr-3 ml-1 my-0 rounded-full p-1.5"
        :class="circleBgClass"
      >
        <RuiIcon
          size="18"
          :name="icon"
        />
      </div>
      <div class="flex-1 text-truncate">
        <div
          class="font-medium text-truncate"
          :title="notification.title"
        >
          {{ notification.title }}
        </div>
        <TimeAgoDisplay
          class="text-caption text-rui-text-secondary -mt-0.5 block"
          :timestamp="timestamp"
          milliseconds
        />
      </div>
      <RuiButton
        data-id="notification_dismiss"
        variant="text"
        icon
        class="p-2!"
        @click="dismiss(notification.id)"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>
    <div
      class="mt-1 px-2 break-words text-rui-text-secondary text-body-2 group overflow-hidden whitespace-pre-line relative transition-all"
      :class="{
        'cursor-pointer': showExpandArrow && !expanded,
      }"
      :style="messageWrapperStyle"
      @click="messageClicked()"
    >
      <div
        ref="message"
        :class="{
          'max-h-[calc(100vh-15rem)] overflow-auto': popup && expanded,
        }"
      >
        <div :title="notification.message">
          {{ notification.message }}
        </div>
      </div>
      <!-- only a cue that the message goes on; the Show more button below opens it -->
      <div
        v-if="showExpandArrow && !expanded"
        class="pointer-events-none h-8 bg-linear-to-b from-transparent absolute bottom-0 inset-x-0"
        :class="expandButtonClass"
      />
    </div>
    <div class="flex mt-1 gap-x-2 gap-y-0.5 flex-wrap mx-0.5 max-w-full overflow-auto">
      <RuiButton
        v-if="showExpandArrow"
        color="primary"
        variant="text"
        size="sm"
        class="order-last ms-auto"
        :aria-expanded="expanded"
        data-id="notification_expand"
        @click="buttonClicked()"
      >
        {{ expanded ? t('notification_sidebar.show_less') : t('notification_sidebar.show_more') }}
        <template #append>
          <RuiIcon
            :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'"
            size="16"
          />
        </template>
      </RuiButton>
      <RuiButton
        v-for="(action, index) in actions"
        :key="index"
        :color="action.danger ? 'error' : 'primary'"
        variant="text"
        size="sm"
        @click="doAction(action)"
      >
        {{ action.label }}
        <template #append>
          <RuiIcon
            :name="getIcon(action)"
            size="16"
          />
        </template>
      </RuiButton>
      <RuiButton
        v-if="notification.severity === Severity.ERROR"
        color="primary"
        variant="text"
        size="sm"
        @click="copy()"
      >
        {{ t('common.actions.copy') }}
        <template #append>
          <RuiIcon
            name="lu-copy"
            size="16"
          />
        </template>
      </RuiButton>
    </div>
  </RuiCard>
</template>
