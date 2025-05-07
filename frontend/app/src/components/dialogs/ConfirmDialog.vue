<script setup lang="ts">
import { DialogType, themes } from '@/types/dialogs';

const props = withDefaults(defineProps<{
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
}>(), {
  confirmType: DialogType.INFO,
  disabled: false,
  loading: false,
  maxWidth: '500',
  primaryAction: null,
  secondaryAction: null,
  singleAction: false,
});

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

const { confirmType, primaryAction, secondaryAction } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const color = computed(() => themes[get(confirmType)].color);
const icon = computed(() => themes[get(confirmType)].icon);
const primaryText = computed<string>(() => get(primaryAction) || t('common.actions.confirm'));
const secondaryText = computed<string>(() => get(secondaryAction) || t('common.actions.cancel'));
</script>

<template>
  <RuiDialog
    :model-value="display"
    persistent
    z-index="10000"
    :max-width="maxWidth"
    @keydown.esc.stop="emit('cancel')"
    @keydown.enter.stop="emit('confirm')"
  >
    <RuiCard data-cy="confirm-dialog">
      <template #header>
        <h5
          class="text-h5"
          data-cy="dialog-title"
        >
          {{ title }}
        </h5>
      </template>

      <div class="flex gap-4">
        <div>
          <RuiIcon
            :color="color"
            size="36"
            :name="icon"
          />
        </div>
        <div class="text-body-1 pt-1 w-full break-words whitespace-pre-line">
          {{ message }}
          <slot />
        </div>
      </div>

      <template #footer>
        <div class="grow" />
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
      </template>
    </RuiCard>
  </RuiDialog>
</template>
