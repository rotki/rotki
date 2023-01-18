<script setup lang="ts">
import { DialogType, themes } from '@/types/dialogs';

const props = withDefaults(
  defineProps<{
    title: string;
    message: string;
    display: boolean;
    primaryAction?: string | null;
    secondaryAction?: string | null;
    confirmType?: DialogType;
    disabled?: boolean;
    singleAction?: boolean;
    loading?: boolean;
    maxWidth?: string;
  }>(),
  {
    primaryAction: null,
    secondaryAction: null,
    confirmType: DialogType.INFO,
    disabled: false,
    singleAction: false,
    loading: false,
    maxWidth: '500'
  }
);

const emit = defineEmits<{
  (e: 'confirm'): void;
  (e: 'cancel'): void;
}>();

const { confirmType, primaryAction, secondaryAction } = toRefs(props);

const { tc } = useI18n();

const color = computed(() => themes[get(confirmType)].color);
const icon = computed(() => themes[get(confirmType)].icon);

const primaryText = computed(() => {
  return get(primaryAction) || tc('common.actions.confirm');
});

const secondaryText = computed(() => {
  return get(secondaryAction) || tc('common.actions.cancel');
});
</script>

<template>
  <v-dialog-transition>
    <v-dialog
      v-if="display"
      :value="true"
      persistent
      :max-width="maxWidth"
      class="confirm-dialog"
      @keydown.esc.stop="emit('cancel')"
    >
      <v-card data-cy="confirm-dialog">
        <v-card-title
          class="confirm-dialog__title text-h5"
          data-cy="dialog-title"
        >
          {{ title }}
        </v-card-title>
        <v-card-text class="confirm-dialog__text">
          <v-row align="center">
            <v-col cols="auto" class="text-center">
              <v-icon :color="color" x-large>
                {{ icon }}
              </v-icon>
            </v-col>
            <v-col class="text-body-1">
              {{ message }}
              <slot />
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="confirm-dialog__actions">
          <v-spacer />
          <v-btn
            v-if="!singleAction"
            depressed
            outlined
            text
            data-cy="button-cancel"
            @click="emit('cancel')"
          >
            {{ secondaryText }}
          </v-btn>
          <v-btn
            :color="color"
            depressed
            :disabled="disabled"
            data-cy="button-confirm"
            :loading="loading"
            @click="emit('confirm')"
          >
            {{ primaryText }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog-transition>
</template>

<style scoped lang="scss">
.confirm-dialog {
  &__actions {
    padding: 16px !important;
  }
}
</style>
