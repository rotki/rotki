<script setup lang="ts">
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useFormErrorScroll } from '@/modules/core/common/use-form-error-scroll';
import BigDialogConfirmButton from '@/modules/shell/components/dialogs/BigDialogConfirmButton.vue';

/** The footer's two buttons. `primary` defaults to Confirm and `secondary` to Cancel. */
export interface BigDialogAction {
  primary?: string;
  secondary?: string;
  disabled?: boolean;
  tooltip?: string;
  hidden?: boolean;
}

/** Validation state the confirm button reports on. */
interface BigDialogErrors {
  count?: number;
  /** Scroll the first error into view when the count goes from zero to non-zero. */
  autoScroll?: boolean;
}

/** Visual knobs a couple of callers tweak; dismissal behaviour is `persistent`/`promptOnClose`. */
interface BigDialogLayout {
  maxWidth?: string;
  divide?: boolean;
  /** Drop the 50vh minimum on the content area. */
  autoHeight?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const {
  action,
  display,
  errors,
  layout,
  loading = false,
  persistent = false,
  promptOnClose = false,
  subtitle = '',
  title,
} = defineProps<{
  title: string;
  subtitle?: string;
  display: boolean;
  loading?: boolean;
  action?: BigDialogAction;
  layout?: BigDialogLayout;
  errors?: BigDialogErrors;
  persistent?: boolean;
  promptOnClose?: boolean;
}>();

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

const wrapper = useTemplateRef('wrapper');

const { show } = useConfirmStore();
const { t } = useI18n({ useScope: 'global' });
const { scrollToFirstError } = useFormErrorScroll();

// Each field is read on its own rather than by spreading a bag over defaults: a caller forwarding
// its own optional value passes a present key holding `undefined`, which a spread takes as the value.
const errorCount = computed<number>(() => errors?.count ?? 0);

const actionDisabled = computed<boolean>(() => action?.disabled ?? false);

const actionHidden = computed<boolean>(() => action?.hidden ?? false);

const actionTooltip = computed<string>(() => action?.tooltip ?? '');

const maxWidth = computed<string>(() => layout?.maxWidth ?? '900px');

const divide = computed<boolean>(() => layout?.divide ?? false);

const autoHeight = computed<boolean>(() => layout?.autoHeight ?? false);

const hasErrors = computed<boolean>(() => get(errorCount) > 0);

watch(errorCount, async (newCount, oldCount) => {
  if (errors?.autoScroll && newCount > 0 && oldCount === 0) {
    await nextTick();
    await scrollToFirstError(get(wrapper) ?? undefined);
  }
});

// `||` rather than `??` on purpose: an empty label falls back to the default, as it always has.
const primary = computed(() => action?.primary || t('common.actions.confirm'));
const secondary = computed(() => action?.secondary || t('common.actions.cancel'));
const displayModel = computed({
  get() {
    return display;
  },
  set(value) {
    if (!value)
      cancel();
  },
});

function confirm(): void {
  if (loading)
    return;

  emit('confirm');
}

function cancel() {
  return emit('cancel');
}

function promptClose() {
  if (!promptOnClose)
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
        data-testid="bottom-dialog"
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
          class="overflow-y-auto -mx-4 px-4 -mt-4 pt-2 pb-4 max-h-[calc(90vh-190px)]"
          :class="{ 'min-h-[50vh]': !autoHeight }"
        >
          <slot :wrapper="wrapper" />
        </div>

        <RuiDivider class="mb-4 -mx-4" />

        <slot name="footer">
          <div class="flex gap-2 w-full">
            <slot name="left-buttons" />
            <div class="grow" />
            <RuiButton
              color="primary"
              variant="outlined"
              data-testid="cancel"
              @click="cancel()"
            >
              {{ secondary }}
            </RuiButton>
            <RuiTooltip
              v-if="!actionHidden"
              :disabled="!actionTooltip"
              :options="{ placement: 'top' }"
              tooltip-class="max-w-80"
            >
              <template #activator>
                <BigDialogConfirmButton
                  :primary="primary"
                  :has-errors="hasErrors"
                  :action-disabled="actionDisabled"
                  :loading="loading"
                  :error-count="errorCount"
                />
              </template>
              {{ actionTooltip }}
            </RuiTooltip>
          </div>
        </slot>
      </RuiCard>
    </form>
  </RuiBottomSheet>
</template>
