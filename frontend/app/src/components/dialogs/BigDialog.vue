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
    maxWidth?: string;
    persistent?: boolean;
  }>(),
  {
    subtitle: '',
    loading: false,
    actionDisabled: false,
    primaryAction: () => null,
    secondaryAction: () => null,
    confirmType: DialogType.INFO,
    maxWidth: '900px',
    persistent: false
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

const css = useCssModule();
</script>

<template>
  <VBottomSheet
    :value="display"
    v-bind="$attrs"
    over
    :persistent="persistent"
    class="big-dialog"
    width="98%"
    :max-width="maxWidth"
    @click:outside="!persistent && cancel()"
    @keydown.esc.stop="!persistent && cancel()"
    @input="!persistent && cancel()"
  >
    <RuiCard data-cy="bottom-dialog" class="!rounded-b-none">
      <template #header> {{ title }}</template>
      <template v-if="subtitle" #subheader> {{ subtitle }}</template>
      <div
        v-if="display"
        class="overflow-y-auto -mx-4 px-4 -mt-2 pt-2 pb-4"
        :class="css.card"
      >
        <slot />
      </div>

      <RuiDivider class="mb-4 -mx-4" />

      <slot name="footer">
        <div class="flex flex-row gap-2 w-full">
          <div class="grow" />
          <RuiButton
            color="primary"
            variant="outlined"
            data-cy="cancel"
            @click="cancel()"
          >
            {{ secondary }}
          </RuiButton>
          <RuiButton
            data-cy="confirm"
            :color="themes[confirmType].color"
            :disabled="actionDisabled || loading"
            :loading="loading"
            @click="confirm()"
          >
            {{ primary }}
          </RuiButton>
        </div>
      </slot>
    </RuiCard>
  </VBottomSheet>
</template>

<style module lang="scss">
.card {
  max-height: calc(90vh - 190px);
  min-height: 50vh;
}
</style>
