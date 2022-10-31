<template>
  <v-card :class="$style.notification" :outlined="!popup" :elevation="0">
    <v-list-item :class="$style.body">
      <v-list-item-avatar>
        <v-icon size="32px" :color="color">
          {{ icon }}
        </v-icon>
      </v-list-item-avatar>
      <v-list-item-content>
        <v-list-item-title class="mt-2">
          {{ notification.title }}
        </v-list-item-title>
        <span class="mt-1" :style="fontStyle" :class="$style.message">
          {{ notification.message }}
        </span>
        <span class="text-caption text--secondary">
          {{ date }}
        </span>
        <slot />
      </v-list-item-content>
      <div class="d-flex flex-column" :class="$style.actions">
        <v-tooltip bottom open-delay="400">
          <template #activator="{ on }">
            <v-btn
              text
              icon
              :class="$style.dismiss"
              v-on="on"
              @click="dismiss(notification.id)"
            >
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </template>
          <span>{{ t('notification.dismiss_tooltip') }}</span>
        </v-tooltip>
        <v-tooltip bottom open-delay="400">
          <template #activator="{ on }">
            <v-btn :class="$style.copy" text icon v-on="on" @click="copy()">
              <v-icon>mdi-content-copy</v-icon>
            </v-btn>
          </template>
          <span> {{ t('notification.copy_tooltip') }}</span>
        </v-tooltip>
      </div>
    </v-list-item>
  </v-card>
</template>

<script setup lang="ts">
import { NotificationData, Severity } from '@rotki/common/lib/messages';
import dayjs from 'dayjs';
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';

const props = defineProps({
  popup: { required: false, type: Boolean, default: false },
  notification: {
    required: true,
    type: Object as PropType<NotificationData>
  }
});

const emit = defineEmits(['dismiss']);

const { t } = useI18n();

const { notification } = toRefs(props);
const dismiss = (id: number) => {
  emit('dismiss', id);
};

const icon = computed(() => {
  switch (get(notification).severity) {
    case Severity.ERROR:
      return 'mdi-alert-circle';
    case Severity.INFO:
      return 'mdi-information-outline';
    case Severity.WARNING:
      return 'mdi-alert';
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

const date = computed(() => {
  return dayjs(get(notification).date).format('LLL');
});

const copy = async () => {
  await navigator.clipboard.writeText(get(notification).message);
};

const { fontStyle } = useTheme();
</script>

<style module lang="scss">
.notification {
  height: 120px;
  max-width: 400px;
}

.body {
  max-width: 400px;
  height: 100% !important;
  padding: 8px !important;
}

.message {
  font-size: 13px;
  min-height: 60px;
  max-height: 60px;
  overflow-y: auto;
  white-space: pre-line;
}

.dismiss {
  position: absolute;
  right: 0;
  top: 0;
}

.copy {
  position: absolute;
  right: 0;
  bottom: 4px;
}

.copy-area {
  position: absolute;
  left: -999em;
}

.actions {
  height: 100%;
  justify-content: space-between;
  margin-right: -4px;
}
</style>
