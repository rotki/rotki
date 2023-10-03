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

const { t } = useI18n();

const color = computed(() => themes[get(confirmType)].color);
const icon = computed(() => themes[get(confirmType)].icon);

const primaryText = computed(
  () => get(primaryAction) || t('common.actions.confirm')
);

const secondaryText = computed(
  () => get(secondaryAction) || t('common.actions.cancel')
);
</script>

<template>
  <VDialogTransition>
    <VDialog
      v-if="display"
      :value="true"
      persistent
      :max-width="maxWidth"
      class="confirm-dialog"
      @keydown.esc.stop="emit('cancel')"
    >
      <VCard data-cy="confirm-dialog">
        <VCardTitle
          class="confirm-dialog__title text-h5"
          data-cy="dialog-title"
        >
          {{ title }}
        </VCardTitle>
        <VCardText class="confirm-dialog__text">
          <div class="flex gap-4">
            <div>
              <RuiIcon :color="color" size="36" :name="icon" />
            </div>
            <div class="text-body-1">
              {{ message }}
              <slot />
            </div>
          </div>
        </VCardText>

        <VCardActions class="confirm-dialog__actions gap-2">
          <VSpacer />
          <RuiButton
            v-if="!singleAction"
            variant="text"
            color="primary"
            data-cy="button-cancel"
            @click="emit('cancel')"
          >
            {{ secondaryText }}
          </RuiButton>
          <RuiButton
            :color="color"
            :disabled="disabled"
            data-cy="button-confirm"
            :loading="loading"
            @click="emit('confirm')"
          >
            {{ primaryText }}
          </RuiButton>
        </VCardActions>
      </VCard>
    </VDialog>
  </VDialogTransition>
</template>
