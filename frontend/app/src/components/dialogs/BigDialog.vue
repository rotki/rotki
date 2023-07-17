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
const emit = defineEmits<{
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const { t } = useI18n();

const { subtitle, primaryAction, secondaryAction } = toRefs(props);

const primary = computed(
  () => get(primaryAction) || t('common.actions.confirm')
);
const secondary = computed(
  () => get(secondaryAction) || t('common.actions.cancel')
);

const confirm = () => emit('confirm');
const cancel = () => emit('cancel');

const contentStyle = computed(() => {
  const height = 118 + (get(subtitle) ? 26 : 0);
  return { height: `calc(90vh - ${height}px)` };
});
</script>

<template>
  <VBottomSheet
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
    <VCard class="big-dialog" data-cy="bottom-dialog">
      <VCardTitle>
        <CardTitle>
          {{ title }}
        </CardTitle>
      </VCardTitle>
      <VCardSubtitle v-if="subtitle">
        {{ subtitle }}
      </VCardSubtitle>
      <div class="big-dialog__content" :style="contentStyle">
        <div class="big-dialog__body">
          <slot v-if="display" />
        </div>
      </div>
      <VSheet>
        <VCardActions>
          <VSpacer />
          <VBtn
            color="primary"
            depressed
            outlined
            text
            class="big-dialog__buttons__cancel"
            @click="cancel()"
          >
            {{ secondary }}
          </VBtn>
          <VBtn
            data-cy="confirm"
            :color="themes[confirmType].color"
            :disabled="actionDisabled || loading"
            :loading="loading"
            depressed
            class="big-dialog__buttons__confirm"
            @click="confirm()"
          >
            {{ primary }}
          </VBtn>
        </VCardActions>
      </VSheet>
    </VCard>
  </VBottomSheet>
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
