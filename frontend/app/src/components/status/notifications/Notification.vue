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
      return 'mdi-information-outline';
    case Severity.WARNING:
      return 'mdi-alarm-light-outline';
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
  <VCard
    :class="[
      css.notification,
      {
        [css.action]: !!notification.action,
        [css['fixed-height']]: !popup
      }
    ]"
    :outlined="!popup"
    :elevation="0"
  >
    <VListItem :class="css.body" class="flex-col items-stretch">
      <div class="flex pa-1">
        <VListItemAvatar class="mr-3 ml-1 my-0" :color="color">
          <VIcon size="24px" color="white">
            {{ icon }}
          </VIcon>
        </VListItemAvatar>
        <VListItemContent class="py-0">
          <VListItemTitle>
            {{ notification.title }}
          </VListItemTitle>
          <VListItemSubtitle>
            {{ date }}
          </VListItemSubtitle>
        </VListItemContent>
        <VTooltip bottom open-delay="400" z-index="9999">
          <template #activator="{ on }">
            <VBtn text icon v-on="on" @click="dismiss(notification.id)">
              <VIcon>mdi-close</VIcon>
            </VBtn>
          </template>
          <span>{{ t('notification.dismiss_tooltip') }}</span>
        </VTooltip>
      </div>
      <div
        class="mt-1 px-2 text-rui-text"
        :class="[css.message, { [css.inline]: !popup }]"
      >
        <MissingKeyNotification
          v-if="notification.i18nParam"
          :params="notification.i18nParam"
        />
        <div v-else>
          {{ notification.message }}
        </div>
      </div>
      <slot />
      <div class="flex mt-auto items-center ml-n1">
        <div v-if="notification.action" class="flex items-start mr-2">
          <VBtn
            color="primary"
            depressed
            small
            plain
            text
            @click="action(notification)"
          >
            {{ notification.action.label }}
            <VIcon class="ml-1" small>mdi-arrow-right</VIcon>
          </VBtn>
        </div>
        <VTooltip bottom open-delay="400" z-index="9999">
          <template #activator="{ on }">
            <VBtn color="primary" small plain text v-on="on" @click="copy()">
              {{ t('notification.copy') }}
              <VIcon class="ml-1" x-small>mdi-content-copy</VIcon>
            </VBtn>
          </template>
          <span> {{ t('notification.copy_tooltip') }}</span>
        </VTooltip>
      </div>
    </VListItem>
  </VCard>
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
  padding: 8px !important;

  &::after {
    display: none;
  }
}

.message {
  font-size: 14px;
  max-height: 60px;
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
