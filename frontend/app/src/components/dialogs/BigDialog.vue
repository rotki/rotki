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
    <Card contained data-cy="bottom-dialog">
      <template #title> {{ title }}</template>
      <template v-if="subtitle" #subtitle> {{ subtitle }}</template>
      <slot v-if="display" />
      <template #buttons>
        <div class="flex flex-row gap-2 w-full">
          <div class="grow" />
          <RuiButton
            color="primary"
            variant="outlined"
            class="big-dialog__buttons__cancel"
            @click="cancel()"
          >
            {{ secondary }}
          </RuiButton>
          <RuiButton
            data-cy="confirm"
            :color="themes[confirmType].color"
            :disabled="actionDisabled || loading"
            :loading="loading"
            class="big-dialog__buttons__confirm"
            @click="confirm()"
          >
            {{ primary }}
          </RuiButton>
        </div>
      </template>
    </Card>
  </VBottomSheet>
</template>
