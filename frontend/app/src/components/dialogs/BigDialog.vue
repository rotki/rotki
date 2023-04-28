<script setup lang="ts">
import { DialogType, themes } from '@/types/dialogs';

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    display: boolean;
    loading?: boolean;
    actionDisabled?: boolean;
    primaryAction?: string | null;
    secondaryAction?: string | null;
    confirmType?: DialogType;
  }>(),
  {
    subtitle: '',
    loading: false,
    actionDisabled: false,
    primaryAction: () => null,
    secondaryAction: () => null,
    confirmType: DialogType.INFO
  }
);
const { tc } = useI18n();

const { subtitle, primaryAction, secondaryAction } = toRefs(props);

const primary = computed(
  () => get(primaryAction) || tc('common.actions.confirm')
);
const secondary = computed(
  () => get(secondaryAction) || tc('common.actions.cancel')
);

const emit = defineEmits<{
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const confirm = () => emit('confirm');
const cancel = () => emit('cancel');

const contentStyle = computed(() => {
  const height = 118 + (get(subtitle) ? 26 : 0);
  return { height: `calc(90vh - ${height}px)` };
});
</script>

<template>
  <v-bottom-sheet
    :value="display"
    v-bind="$attrs"
    over
    class="big-dialog"
    width="98%"
    max-width="900px"
    @click:outside="cancel()"
    @keydown.esc.stop="cancel()"
    @input="cancel()"
  >
    <v-card class="big-dialog" data-cy="bottom-dialog">
      <v-card-title>
        <card-title>
          {{ title }}
        </card-title>
      </v-card-title>
      <v-card-subtitle v-if="subtitle">
        {{ subtitle }}
      </v-card-subtitle>
      <div class="big-dialog__content" :style="contentStyle">
        <div class="big-dialog__body">
          <slot v-if="display" />
        </div>
      </div>
      <v-sheet>
        <v-card-actions>
          <v-progress-linear v-if="loading" indeterminate class="mx-4" />
          <v-spacer />
          <v-btn
            color="primary"
            depressed
            outlined
            text
            class="big-dialog__buttons__cancel"
            @click="cancel()"
          >
            {{ secondary }}
          </v-btn>
          <v-btn
            data-cy="confirm"
            :color="themes[confirmType].color"
            :disabled="actionDisabled"
            depressed
            class="big-dialog__buttons__confirm"
            @click="confirm()"
          >
            {{ primary }}
          </v-btn>
        </v-card-actions>
      </v-sheet>
    </v-card>
  </v-bottom-sheet>
</template>

<style scoped lang="scss">
.big-dialog {
  &__body {
    padding: 0 1.5rem;
  }

  &__content {
    overflow-y: auto;
  }
}

:deep(.v-card) {
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;

  .v-card {
    &__actions {
      padding: 1rem 1.5rem !important;
    }
  }
}
</style>
