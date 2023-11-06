<script setup lang="ts">
import { type NotificationData, Severity } from '@rotki/common/lib/messages';
import dayjs from 'dayjs';

const props = withDefaults(
  defineProps<{
    notification: NotificationData;
    popup?: boolean;
  }>(),
  { popup: false }
);

const emit = defineEmits<{ (e: 'dismiss', id: number): void }>();

const css = useCssModule();
const { t } = useI18n();
const { copy: copyToClipboard } = useClipboard();

const { notification } = toRefs(props);
const dismiss = (id: number) => {
  emit('dismiss', id);
};

const icon = computed(() => {
  switch (get(notification).severity) {
    case Severity.ERROR:
    case Severity.INFO:
      return 'error-warning-line';
    case Severity.WARNING:
      return 'alarm-warning-line';
  }
  return '';
});

const color = computed(() => {
  switch (get(notification).severity) {
    case Severity.ERROR:
      return 'error';
    case Severity.INFO:
      return 'info';
    case Severity.WARNING:
      return 'warning';
  }
  return '';
});

const date = computed(() => dayjs(get(notification).date).format('LLL'));

const copy = async () => {
  const { message, i18nParam } = get(notification);
  let messageText = message;

  if (i18nParam) {
    messageText = t(i18nParam.message, {
      service: i18nParam.props.service,
      location: i18nParam.props.location,
      url: i18nParam.props.url
    }).toString();
  }
  await copyToClipboard(messageText);
};

const action = async (notification: NotificationData) => {
  const action = notification.action?.action;
  action?.();
  dismiss(notification.id);
};
</script>

<template>
  <RuiCard
    :class="[
      css.notification,
      {
        [css.action]: !!notification.action,
        [css['fixed-height']]: !popup,
        ['!rounded-none']: popup
      }
    ]"
    class="[&>div]:!p-2"
    :variant="popup ? 'flat' : 'outlined'"
  >
    <VListItem :class="css.body" class="flex-col items-stretch p-0">
      <div class="flex pa-1">
        <VListItemAvatar class="mr-3 ml-1 my-0" :color="color">
          <div>
            <RuiIcon size="24" class="text-white" :name="icon" />
          </div>
        </VListItemAvatar>
        <VListItemContent class="py-0">
          <VListItemTitle :title="notification.title">
            {{ notification.title }}
          </VListItemTitle>
          <VListItemSubtitle>
            {{ date }}
          </VListItemSubtitle>
        </VListItemContent>
        <RuiTooltip
          :popper="{ placement: 'bottom', offsetDistance: 0 }"
          open-delay="400"
          class="z-[9999]"
        >
          <template #activator>
            <RuiButton variant="text" icon @click="dismiss(notification.id)">
              <RuiIcon name="close-line" />
            </RuiButton>
          </template>
          <span>{{ t('notification.dismiss_tooltip') }}</span>
        </RuiTooltip>
      </div>
      <div
        class="mt-1 px-2 text-rui-text break-words text-sm leading-2"
        :class="[css.message, { [css.inline]: !popup }]"
      >
        <MissingKeyNotification
          v-if="notification.i18nParam"
          :params="notification.i18nParam"
        />
        <div v-else :title="notification.message">
          {{ notification.message }}
        </div>
      </div>
      <slot />
      <div class="flex mt-auto items-center mx-0.5">
        <div v-if="notification.action" class="flex items-start mr-2">
          <RuiButton
            color="primary"
            variant="text"
            size="sm"
            @click="action(notification)"
          >
            {{ notification.action.label }}
            <template #append>
              <RuiIcon name="arrow-right-line" size="16" />
            </template>
          </RuiButton>
        </div>
        <RuiTooltip
          :popper="{ placement: 'bottom', offsetDistance: 0 }"
          open-delay="400"
          class="z-[9999]"
        >
          <template #activator>
            <RuiButton color="primary" variant="text" size="sm" @click="copy()">
              {{ t('notification.copy') }}
              <template #append>
                <RuiIcon name="file-copy-line" size="16" />
              </template>
            </RuiButton>
          </template>
          <span> {{ t('notification.copy_tooltip') }}</span>
        </RuiTooltip>
      </div>
    </VListItem>
  </RuiCard>
</template>

<style module lang="scss">
.notification {
  max-width: 400px;

  &.fixed-height {
    height: 164px;
  }

  &.action {
    background-color: rgba(237, 108, 2, 0.12);
  }
}

.body {
  max-width: 400px;
  height: 100% !important;

  &::after {
    display: none;
  }
}

.message {
  height: 60px;
  overflow-y: auto;
  white-space: pre-line;

  .inline {
    min-height: 60px;
  }
}

.copy-area {
  position: absolute;
  left: -999em;
}
</style>
