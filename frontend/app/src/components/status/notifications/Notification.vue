<script setup lang="ts">
import { type NotificationAction, type NotificationData, Severity } from '@rotki/common/lib/messages';
import dayjs from 'dayjs';

const props = withDefaults(
  defineProps<{
    notification: NotificationData;
    popup?: boolean;
  }>(),
  { popup: false },
);

const emit = defineEmits<{ (e: 'dismiss', id: number): void }>();

const css = useCssModule();
const { t } = useI18n();
const { copy: copyToClipboard } = useClipboard();

const { notification } = toRefs(props);

const actions: ComputedRef<NotificationAction[]> = computed(() => {
  const action = get(notification).action;

  if (!action)
    return [];
  if (!Array.isArray(action))
    return [action];

  return action;
});

function dismiss(id: number) {
  emit('dismiss', id);
}

const icon = computed(() => {
  switch (get(notification).severity) {
    case Severity.ERROR:
    case Severity.INFO:
      return 'error-warning-line';
    case Severity.WARNING:
      return 'alarm-warning-line';
    case Severity.REMINDER:
      return 'alarm-line';
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
    case Severity.REMINDER:
      return 'reminder';
    default:
      return '';
  }
});

const circleBgClass = computed(() => {
  switch (props.notification.severity) {
    case Severity.ERROR:
      return 'bg-rui-error';
    case Severity.INFO:
      return 'bg-rui-info';
    case Severity.WARNING:
      return 'bg-rui-warning';
    case Severity.REMINDER:
      return 'bg-rui-secondary';
    default:
      return 'bg-rui-success';
  }
});

const date = computed(() => dayjs(get(notification).date).format('LLL'));

async function copy() {
  const { message, i18nParam } = get(notification);
  let messageText = message;

  if (i18nParam) {
    messageText = t(i18nParam.message, {
      service: i18nParam.props.service,
      location: i18nParam.props.location,
      url: i18nParam.props.url,
    }).toString();
  }
  await copyToClipboard(messageText);
}

function doAction(id: number, action: NotificationAction) {
  action.action?.();
  if (!action.persist)
    dismiss(id);
}
</script>

<template>
  <RuiCard
    :class="[
      css.notification,
      {
        [css.action]: !!notification.action,
        [css['fixed-height']]: !popup,
        [css[`bg_${color}`]]: !!color,
        ['!rounded-none']: popup,
      },
    ]"
    class="!p-2 !pb-1.5"
    no-padding
    :variant="popup ? 'flat' : 'outlined'"
  >
    <div
      :class="css.body"
      class="flex-col items-stretch p-0"
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
        <RuiTooltip
          :popper="{ placement: 'bottom', offsetDistance: 0 }"
          :open-delay="400"
          class="z-[9999]"
        >
          <template #activator>
            <RuiButton
              variant="text"
              icon
              class="!p-2"
              @click="dismiss(notification.id)"
            >
              <RuiIcon name="close-line" />
            </RuiButton>
          </template>
          <span>{{ t('notification.dismiss_tooltip') }}</span>
        </RuiTooltip>
      </div>
      <div
        class="mt-1 px-2 break-words text-rui-text-secondary text-xs leading-2"
        :class="[css.message, { [css.inline]: !popup }]"
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
      <slot />
      <div class="flex mt-1 gap-2 mx-0.5">
        <RuiButton
          v-for="(action, index) in actions"
          :key="index"
          color="primary"
          variant="text"
          size="sm"
          @click="doAction(notification.id, action)"
        >
          {{ action.label }}
          <template #append>
            <RuiIcon
              :name="action.icon ?? 'arrow-right-line'"
              size="16"
            />
          </template>
        </RuiButton>
        <RuiTooltip
          :popper="{ placement: 'bottom', offsetDistance: 0 }"
          :open-delay="400"
          class="z-[9999]"
        >
          <template #activator>
            <RuiButton
              color="primary"
              variant="text"
              size="sm"
              @click="copy()"
            >
              {{ t('notification.copy') }}
              <template #append>
                <RuiIcon
                  name="file-copy-line"
                  size="16"
                />
              </template>
            </RuiButton>
          </template>
          <span> {{ t('notification.copy_tooltip') }}</span>
        </RuiTooltip>
      </div>
    </div>
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

  @each $color in (warning, error, info) {
    &.bg_#{$color} {
      @apply bg-rui-#{$color}/[.1] #{!important};
    }
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
  height: 64px;
  overflow-y: auto;
  white-space: pre-line;

  .inline {
    min-height: 64px;
  }
}

.copy-area {
  position: absolute;
  left: -999em;
}
</style>
