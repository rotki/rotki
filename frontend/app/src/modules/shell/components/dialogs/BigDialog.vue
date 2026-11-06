<script setup lang="ts">
import type { RuiCardClassNames } from '@rotki/ui-library';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { useFormErrorFocus } from '@/modules/core/common/use-form-error-focus';
import BigDialogConfirmButton from '@/modules/shell/components/dialogs/BigDialogConfirmButton.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

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
  /**
   * Reveal the first error when the count goes from zero to non-zero.
   *
   * @remarks
   * Confirming already reveals whatever validation rejected, so this is for the errors that arrive
   * later than that: the ones the backend reports against a field once the save has been attempted.
   */
  autoFocus?: boolean;
}

/** Visual knobs a couple of callers tweak; dismissal behaviour is `persistent`/`promptOnClose`. */
export interface BigDialogLayout {
  maxWidth?: string;
  divide?: boolean;
  /** Drop the 50vh minimum on the content area. */
  autoHeight?: boolean;
  /**
   * Bound the content area without scrolling it, so the slot scrolls on its own
   * (a `ScrollableDialogContent` with `fill`) and can keep a toolbar above the table in view.
   */
  fill?: boolean;
  /**
   * Hold the sheet at a fixed height whatever its content holds.
   *
   * @remarks
   * The sheet is anchored to the bottom, so content that grows or shrinks moves the header and
   * everything in it. A form whose fields change under a control in the header sets this, so the
   * control stays where the user clicked it. The sheet takes 90% of the window and the content
   * fills what the header and footer leave, whatever the header holds.
   */
  fixedHeight?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const {
  action,
  display,
  errors,
  failure,
  failureTitle = '',
  layout,
  loading = false,
  onConfirm,
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
  /**
   * Why the last save failed, named above the content while the form keeps what was typed.
   *
   * @remarks
   * Shown in the header, outside the scroll area, so it is in view however far the form scrolled.
   * Confirm is the retry, so the strip offers none. Usually `useSaveFailure().failure`.
   */
  failure?: unknown;
  failureTitle?: string;
  /**
   * The save, bound as `@confirm`. A prop rather than an emit so the dialog can wait for it.
   *
   * @remarks
   * Returning the save's promise is what lets the dialog reveal the errors the backend reports
   * against a field, and keeps the confirm button disabled until the save settles.
   */
  onConfirm?: () => unknown;
}>();

const emit = defineEmits<{
  cancel: [];
}>();

defineSlots<{
  'default': (props: { wrapper: HTMLDivElement | null }) => any;
  'footer': () => any;
  'header': (props: { title: string }) => any;
  'subtitle': () => any;
  /** Controls that belong above the content but outside its scroll area, such as a type picker. */
  'header-append': () => any;
  'left-buttons': () => any;
}>();

const wrapper = useTemplateRef('wrapper');
const confirming = ref<boolean>(false);
/** Asking, in the footer, whether to discard the edits. */
const discarding = ref<boolean>(false);
/** Bumped each time the dialog closes, so a save from an earlier opening cannot touch this one. */
let opening = 0;

const { t } = useI18n({ useScope: 'global' });
const { focusFirstError } = useFormErrorFocus(wrapper);

const errorCount = computed<number>(() => errors?.count ?? 0);

const discardQuestion = computed<ConfirmQuestion>(() => ({
  confirmLabel: t('big_dialog.prompt_close.actions.discard'),
  message: t('big_dialog.prompt_close.message'),
}));

const actionDisabled = computed<boolean>(() => action?.disabled ?? false);

const actionHidden = computed<boolean>(() => action?.hidden ?? false);

const actionTooltip = computed<string>(() => action?.tooltip ?? '');

const maxWidth = computed<string>(() => layout?.maxWidth ?? '900px');

const divide = computed<boolean>(() => layout?.divide ?? false);

const autoHeight = computed<boolean>(() => layout?.autoHeight ?? false);

const fill = computed<boolean>(() => layout?.fill ?? false);
const fixedHeight = computed<boolean>(() => layout?.fixedHeight ?? false);

const cardClassNames = computed<RuiCardClassNames>(() => (get(fixedHeight)
  ? { content: 'flex-1 min-h-0 flex flex-col', root: 'rounded-b-none! h-[90vh] flex flex-col' }
  : { root: 'rounded-b-none!' }));

const hasErrors = computed<boolean>(() => get(errorCount) > 0);

const busy = computed<boolean>(() => loading || get(confirming));

watch(() => display, (shown) => {
  if (shown)
    return;
  forgetPendingSave();
  set(discarding, false);
});

watch(errorCount, async (newCount, oldCount) => {
  if (errors?.autoFocus && newCount > 0 && oldCount === 0)
    await focusFirstError();
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

/**
 * Hands the save to the owner of the dialog, waits for it, then reveals whatever it rejected.
 *
 * @remarks
 * Waiting covers both kinds of rejection: the form's own validation, marked while the save runs,
 * and the field errors the backend reports once the request comes back. Doing it here rather than
 * behind the error count is what gives every dialog the behaviour, including the ones that report
 * no count at all.
 */
async function confirm(): Promise<void> {
  if (get(busy))
    return;

  const started = opening;
  set(confirming, true);
  try {
    await onConfirm?.();
  }
  finally {
    if (started === opening)
      set(confirming, false);
  }
  if (started === opening)
    await focusFirstError();
}

/**
 * Forgets a save still running when the dialog closes.
 *
 * @remarks
 * The user may cancel while a save is in flight. Without this, reopening the dialog before that
 * request returns would show a disabled confirm button with nothing on screen to explain it.
 */
function forgetPendingSave(): void {
  opening += 1;
  set(confirming, false);
}

function cancel() {
  return emit('cancel');
}

/** The Cancel button, which asks before discarding edits the same way closing the sheet does. */
function cancelClicked(): void {
  if (promptOnClose)
    promptClose();
  else
    cancel();
}

/**
 * Asks in the footer, in place of its buttons, rather than in a second dialog over this one.
 *
 * @remarks
 * A dismissal while the question is up, such as back pressed again, answers it with keep editing,
 * the way dismissing a dialog of its own would.
 */
function promptClose() {
  if (promptOnClose)
    set(discarding, !get(discarding));
}

function discard(): void {
  set(discarding, false);
  set(displayModel, false);
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
    @dismiss="promptClose()"
  >
    <form
      novalidate
      @submit.stop.prevent="confirm()"
    >
      <RuiCard
        :divide="divide"
        data-testid="bottom-dialog"
        :class-names="cardClassNames"
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
            <div
              v-if="$slots['header-append']"
              class="mt-4"
            >
              <slot name="header-append" />
            </div>
            <FailureStrip
              v-if="failure !== undefined"
              class="mt-4"
              :title="failureTitle"
              :failure="failure"
              data-testid="big-dialog-failure"
            />
          </div>
        </template>
        <div
          v-if="display"
          ref="wrapper"
          class="-mx-4 px-4 -mt-4 pt-2 pb-4"
          :class="{
            'max-h-[calc(90vh-190px)]': !fixedHeight,
            'min-h-[50vh]': !autoHeight && !fixedHeight,
            'flex-1 min-h-0': fixedHeight,
            'overflow-y-auto': !fill,
            'flex flex-col overflow-hidden': fill,
          }"
        >
          <slot :wrapper="wrapper" />
        </div>

        <RuiDivider class="mb-4 -mx-4" />

        <InlineConfirm
          v-if="discarding"
          class="w-full"
          :question="discardQuestion"
          :cancel-label="t('big_dialog.prompt_close.actions.keep_editing')"
          @cancel="discarding = false"
          @confirm="discard()"
        />
        <slot
          v-else
          name="footer"
        >
          <div class="flex gap-2 w-full">
            <slot name="left-buttons" />
            <div class="grow" />
            <RuiButton
              color="primary"
              variant="outlined"
              data-testid="cancel"
              @click="cancelClicked()"
            >
              {{ secondary }}
            </RuiButton>
            <RuiTooltip
              v-if="!actionHidden"
              :disabled="!actionTooltip"
              :options="{ placement: 'top' }"
              :class-names="{ tooltip: 'max-w-80' }"
            >
              <template #activator>
                <BigDialogConfirmButton
                  :primary="primary"
                  :has-errors="hasErrors"
                  :action-disabled="actionDisabled"
                  :loading="busy"
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
