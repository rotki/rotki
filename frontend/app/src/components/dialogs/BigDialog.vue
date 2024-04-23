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
    divide?: boolean;
    autoHeight?: boolean;
  }>(),
  {
    subtitle: '',
    loading: false,
    actionDisabled: false,
    primaryAction: () => null,
    secondaryAction: () => null,
    confirmType: DialogType.INFO,
    maxWidth: '900px',
    persistent: false,
    divide: false,
    autoHeight: false,
  },
);
const emit = defineEmits<{
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const { t } = useI18n();

const { subtitle, primaryAction, secondaryAction } = toRefs(props);
const wrapper = ref<HTMLElement>();

const primary = computed(
  () => get(primaryAction) || t('common.actions.confirm'),
);
const secondary = computed(
  () => get(secondaryAction) || t('common.actions.cancel'),
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
    <RuiCard
      :divide="divide"
      data-cy="bottom-dialog"
      class="!rounded-b-none"
    >
      <template #header>
        <slot name="header">
          {{ title }}
        </slot>
      </template>
      <template
        v-if="subtitle || $slots.subtitle"
        #subheader
      >
        <slot name="subtitle">
          {{ subtitle }}
        </slot>
      </template>
      <div
        v-if="display"
        ref="wrapper"
        class="overflow-y-auto -mx-4 px-4 -mt-4 pt-2 pb-4"
        :class="[css.card, { [css['auto-height']]: autoHeight }]"
      >
        <slot :wrapper="wrapper" />
      </div>

      <RuiDivider class="mb-4 -mx-4" />

      <slot name="footer">
        <div class="flex flex-row gap-2 w-full">
          <slot name="left-buttons" />
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

  &:not(.auto-height) {
    min-height: 50vh;
  }
}
</style>
