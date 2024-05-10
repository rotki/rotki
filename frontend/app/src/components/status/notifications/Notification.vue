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
  if (get(notification).action)
    return 'warning';

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

const message = ref();
const MAX_HEIGHT = 64;

const { height } = useElementSize(message);

const showExpandArrow = computed(() => get(height) > MAX_HEIGHT);
const expanded: Ref<boolean> = ref(false);

const messageWrapperStyle = computed(() => {
  if (!get(showExpandArrow))
    return {};

  const usedHeight = get(expanded) ? get(height) + 24 : MAX_HEIGHT;
  return {
    height: `${usedHeight}px`,
  };
});

function messageClicked() {
  if (!get(showExpandArrow) && get(expanded))
    return;

  set(expanded, true);
}

function buttonClicked() {
  set(expanded, !get(expanded));
}
</script>

<template>
  <RuiCard
    :class="[
      css.notification,
      {
        [css[`bg_${color}`]]: color,
        [css.flat]: !color,
        [css.popup]: popup,
      },
    ]"
    class="!p-2 !pb-1.5"
    no-padding
    :variant="popup ? 'flat' : 'outlined'"
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
      class="mt-1 px-2 break-words text-rui-text-secondary text-body-2 leading-2 group"
      :class="[
        css.message,
        {
          'cursor-pointer': showExpandArrow && !expanded,
          'pb-6': showExpandArrow && expanded,
        },
      ]"
      :style="messageWrapperStyle"
      @click="messageClicked()"
    >
      <div ref="message">
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
        :class="css.expand"
      >
        <RuiButton
          class="!p-0.5"
          :class="css['expand-button']"
          @click.stop="buttonClicked()"
        >
          <RuiIcon
            :name="expanded ? 'arrow-up-s-line' : 'arrow-down-s-line'"
            :class="{ 'invisible opacity-0 group-hover:translate-y-1': !expanded }"
            class="transition-all group-hover:visible group-hover:opacity-100 group-hover:-translate-y-1 text-rui-text-secondary"
            size="20"
          />
        </RuiButton>
      </div>
    </div>
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
  </RuiCard>
</template>

<style module lang="scss">
.notification {
  max-width: 400px;

  &.popup {
    @apply rounded-none #{!important};
  }

  .expand {
    @apply bg-gradient-to-b from-transparent to-white absolute bottom-0 w-full;

    &-button {
      @apply w-full bg-gradient-to-b from-transparent to-white;
      background-color: transparent !important;
    }
  }

  @each $color in (warning, error, info, secondary) {
    &.bg_#{$color} {
      @apply bg-rui-#{$color}/[.1] #{!important};

      .expand {
        &-button {
          @apply to-rui-#{$color}/[.1] #{!important};
        }
      }
    }
  }
}

.message {
  @apply overflow-hidden whitespace-pre-line relative transition-all;
}

:global(.dark) {
  .notification {
    &.flat {
      .expand {
        @apply to-[#1E1E1E];

        &-button {
          @apply to-[#1E1E1E]
        }
      }
    }

    &:not(.flat) {
      .expand {
        @apply to-[#363636];
      }
    }

    &.popup {
      &:not(.flat) {
        .expand {
          @apply to-[#333];
        }
      }
    }
  }
}
</style>
