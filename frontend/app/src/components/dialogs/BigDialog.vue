<script setup lang="ts">
import { useConfirmStore } from '@/store/confirm';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<{
  title: string;
  subtitle?: string;
  display: boolean;
  loading?: boolean;
  actionHidden?: boolean;
  actionDisabled?: boolean;
  primaryAction?: string;
  secondaryAction?: string;
  maxWidth?: string;
  persistent?: boolean;
  divide?: boolean;
  autoHeight?: boolean;
  promptOnClose?: boolean;
}>(), {
  actionDisabled: false,
  actionHidden: false,
  autoHeight: false,
  divide: false,
  loading: false,
  maxWidth: '900px',
  persistent: false,
  primaryAction: undefined,
  promptOnClose: false,
  secondaryAction: undefined,
  subtitle: '',
});

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

defineSlots<{
  'default': (props: { wrapper: HTMLDivElement | null }) => any;
  'footer': () => any;
  'header': (props: { title: string }) => any;
  'subtitle': () => any;
  'left-buttons': () => any;
}>();

const { display, primaryAction, promptOnClose, secondaryAction, subtitle } = toRefs(props);

const wrapper = useTemplateRef('wrapper');

const { show } = useConfirmStore();
const { t } = useI18n({ useScope: 'global' });

const primary = computed(() => get(primaryAction) || t('common.actions.confirm'));
const secondary = computed(() => get(secondaryAction) || t('common.actions.cancel'));
const displayModel = computed({
  get() {
    return get(display);
  },
  set(value) {
    if (!value)
      cancel();
  },
});

function confirm() {
  return emit('confirm');
}

function cancel() {
  return emit('cancel');
}

function promptClose() {
  if (!get(promptOnClose))
    return;

  show({
    message: t('big_dialog.prompt_close.message'),
    primaryAction: t('big_dialog.prompt_close.actions.discard'),
    title: t('big_dialog.prompt_close.title'),
    type: 'info',
  }, async () => {
    set(displayModel, false);
  });
}
</script>

<template>
  <RuiBottomSheet
    v-model="displayModel"
    v-bind="$attrs"
    :persistent="persistent || promptOnClose"
    class="big-dialog"
    width="98%"
    :max-width="maxWidth"
    @click:esc="promptClose()"
    @click:outside="promptClose()"
  >
    <form
      novalidate
      @submit.stop.prevent="confirm()"
    >
      <RuiCard
        :divide="divide"
        data-cy="bottom-dialog"
        class="!rounded-b-none"
      >
        <template #custom-header>
          <div class="m-4">
            <slot
              name="header"
              :title="title"
            >
              <h5 class="font-medium text-xl text-black dark:text-white mb-1">
                {{ title }}
              </h5>
            </slot>
            <div
              v-if="subtitle || $slots.subtitle"
              class="text-sm text-rui-text-secondary"
            >
              <slot name="subtitle">
                {{ subtitle }}
              </slot>
            </div>
          </div>
        </template>
        <div
          v-if="display"
          ref="wrapper"
          class="overflow-y-auto -mx-4 px-4 -mt-4 pt-2 pb-4"
          :class="[$style.card, { [$style['auto-height']]: autoHeight }]"
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
              v-if="!actionHidden"
              data-cy="confirm"
              color="primary"
              :disabled="actionDisabled || loading"
              :loading="loading"
              type="submit"
            >
              {{ primary }}
            </RuiButton>
          </div>
        </slot>
      </RuiCard>
    </form>
  </RuiBottomSheet>
</template>

<style module lang="scss">
.card {
  max-height: calc(90vh - 190px);

  &:not(.auto-height) {
    min-height: 50vh;
  }
}
</style>
