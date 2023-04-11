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

const emit = defineEmits(['dismiss']);

const { t } = useI18n();

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
  await navigator.clipboard.writeText(get(notification).message);
};

const { fontStyle } = useTheme();

const action = async (notification: NotificationData) => {
  const action = notification.action?.action;
  action?.();
  dismiss(notification.id);
};
</script>

<template>
  <v-card
    :class="[
      $style.notification,
      {
        [$style.action]: !!notification.action,
        [$style['fixed-height']]: !popup
      }
    ]"
    :outlined="!popup"
    :elevation="0"
  >
    <v-list-item :class="$style.body" class="flex-column align-stretch">
      <div class="d-flex pa-1">
        <v-list-item-avatar class="mr-3 ml-1 my-0" :color="color">
          <v-icon size="24px" color="white">
            {{ icon }}
          </v-icon>
        </v-list-item-avatar>
        <v-list-item-content class="py-0">
          <v-list-item-title>
            {{ notification.title }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ date }}
          </v-list-item-subtitle>
        </v-list-item-content>
        <v-tooltip bottom open-delay="400" z-index="9999">
          <template #activator="{ on }">
            <v-btn text icon v-on="on" @click="dismiss(notification.id)">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </template>
          <span>{{ t('notification.dismiss_tooltip') }}</span>
        </v-tooltip>
      </div>
      <div
        class="mt-1 px-2"
        :style="fontStyle"
        :class="[$style.message, { [$style.inline]: !popup }]"
      >
        <div>{{ notification.message }}</div>
      </div>
      <slot />
      <div class="d-flex mt-auto align-center ml-n1">
        <div v-if="notification.action" class="d-flex align-start mr-2">
          <v-btn
            color="primary"
            depressed
            small
            plain
            text
            @click="action(notification)"
          >
            {{ notification.action.label }}
            <v-icon class="ml-1" small>mdi-arrow-right</v-icon>
          </v-btn>
        </div>
        <v-tooltip bottom open-delay="400" z-index="9999">
          <template #activator="{ on }">
            <v-btn color="primary" small plain text v-on="on" @click="copy()">
              {{ t('notification.copy') }}
              <v-icon class="ml-1" x-small>mdi-content-copy</v-icon>
            </v-btn>
          </template>
          <span> {{ t('notification.copy_tooltip') }}</span>
        </v-tooltip>
      </div>
    </v-list-item>
  </v-card>
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
