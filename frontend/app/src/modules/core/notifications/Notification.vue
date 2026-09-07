<script setup lang="ts">
import { type NotificationData, Severity } from '@rotki/common';
import MissingKeyNotification from '@/modules/core/notifications/MissingKeyNotification.vue';
import { useNotificationCard } from '@/modules/core/notifications/use-notification-card';

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
  color,
  colorBgClass,
  copy,
  date,
  doAction,
  expandButtonClass,
  expanded,
  getIcon,
  icon,
  messageClicked,
  messageWrapperStyle,
  showExpandArrow,
} = useNotificationCard(() => notification, { dismiss, height });
</script>

<template>
  <RuiCard
    :class="[
      colorBgClass,
      {
        '!rounded-none': popup,
      },
    ]"
    class="!p-2 !pb-1.5 max-w-[400px]"
    no-padding
    :variant="popup ? 'flat' : 'outlined'"
    data-id="notification"
  >
    <div class="flex pb-1 items-center overflow-hidden">
      <div
        class="mr-3 ml-1 my-0 rounded-full p-2"
        :class="circleBgClass"
      >
        <RuiIcon
          size="20"
          class="text-white"
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
        <div class="text-caption text-rui-text-secondary -mt-0.5">
          {{ date }}
        </div>
      </div>
      <RuiButton
        data-id="notification_dismiss"
        variant="text"
        icon
        class="!p-2"
        @click="dismiss(notification.id)"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>
    <div
      class="mt-1 px-2 break-words text-rui-text-secondary text-body-2 leading-2 group overflow-hidden whitespace-pre-line relative transition-all"
      :class="{
        'cursor-pointer': showExpandArrow && !expanded,
        'pb-6': showExpandArrow && expanded,
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
        <MissingKeyNotification
          v-if="notification.i18nParam"
          :params="notification.i18nParam"
        />
        <div
          v-else
          :title="notification.message"
        >
          {{ notification.message }}
        </div>
      </div>
      <div
        v-if="showExpandArrow"
        class="bg-gradient-to-b from-transparent to-white absolute bottom-0 w-full"
        :class="color ? 'dark:to-[#363636]' : 'dark:to-dark-elevated'"
      >
        <RuiButton
          :class="[
            expandButtonClass,
            color ? 'dark:to-[#363636]' : 'dark:to-dark-elevated',
          ]"
          class="!p-0.5 w-full bg-gradient-to-b from-transparent to-white rounded-none !bg-transparent"
          hide-focus-indicator
          @click.stop="buttonClicked()"
        >
          <RuiIcon
            :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'"
            :class="{ 'invisible opacity-0 group-hover:translate-y-1': !expanded }"
            class="transition-all group-hover:visible group-hover:opacity-100 group-hover:-translate-y-1 text-rui-text-secondary"
            size="20"
          />
        </RuiButton>
      </div>
    </div>
    <div class="flex mt-1 gap-x-2 gap-y-0.5 flex-wrap mx-0.5 max-w-full overflow-auto">
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
