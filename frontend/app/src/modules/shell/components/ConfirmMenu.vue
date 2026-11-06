<script setup lang="ts">
import type { RuiMenu } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { startPromise } from '@shared/utils';
import { focusFirstControl } from '@/modules/shell/components/focus-first-control';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';
import { provideConfirmMenuAsk } from '@/modules/shell/components/use-confirm-menu';

interface PendingQuestion {
  question: ConfirmQuestion;
  onAccept: () => void;
  /** The entry that asked, which takes focus back on cancel. */
  asker?: HTMLElement;
}

interface Props {
  /** The menu's width and other classes while it shows its entries; asking always takes `w-72`. */
  menuClass?: string;
}

/**
 * A menu whose entries can ask before they act, in place of the entries rather than in a dialog.
 *
 * @remarks
 * An entry calls `ask(question, onAccept)`, taken from the default slot's props when it is written
 * inline, or from `useConfirmMenuAsk()` when it is a component of its own. The menu then shows the
 * question as a dialog, keeps itself open through the click that asked (so `close-on-content-click`
 * is safe to set), and hides the entries without unmounting them, so the asking entry can still emit
 * once the user accepts. Accepting closes the menu and then runs `onAccept`; cancelling brings the
 * entries back with focus on the entry that asked; closing the menu drops the question.
 *
 * Everything else, such as `options`, `lazy` or `close-on-content-click`, goes to `RuiMenu`.
 */
defineOptions({ inheritAttrs: false });

const open = defineModel<boolean>({ default: false });

const { menuClass } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiMenu, Props>>();

defineSlots<{
  activator: (props: { attrs: Record<string, unknown> }) => any;
  default: (props: { ask: typeof ask }) => any;
}>();

const pending = shallowRef<PendingQuestion>();
const entries = useTemplateRef<HTMLDivElement>('entries');

/** Whether a question was already showing when the current click started. */
let askingAtClick = false;

/** Asks `question` in place of the entries; the entry holding focus, the one just clicked, is the asker. */
function ask(question: ConfirmQuestion, onAccept: () => void): void {
  const asker = document.activeElement instanceof HTMLElement ? document.activeElement : undefined;
  set(pending, { asker, onAccept, question });
}

provideConfirmMenuAsk(ask);

function accept(): void {
  const asked = get(pending);
  set(pending, undefined);
  set(open, false);
  asked?.onAccept();
}

/** Focuses the entry that asked once the entries show again, or their first control if it went. */
async function focusEntries(asker: HTMLElement | undefined): Promise<void> {
  await nextTick();
  const list = get(entries);
  if (asker && list?.contains(asker))
    asker.focus({ preventScroll: true });
  else
    focusFirstControl(list);
}

function cancel(): void {
  const asker = get(pending)?.asker;
  set(pending, undefined);
  startPromise(focusEntries(asker));
}

function startClick(): void {
  askingAtClick = !!get(pending);
}

/**
 * Keeps the menu open through a click that asked a question or answered one.
 *
 * @remarks
 * `RuiMenu` reads `close-on-content-click` on the click's way up, before a re-render could switch it
 * off, so the click stops here, below the menu's own listener, instead.
 */
function endClick(event: MouseEvent): void {
  if (askingAtClick || get(pending))
    event.stopPropagation();
  askingAtClick = false;
}

watch(open, (isOpen) => {
  if (!isOpen)
    set(pending, undefined);
});
</script>

<template>
  <RuiMenu
    v-bind="$attrs"
    v-model="open"
    :role="pending ? 'dialog' : undefined"
    :menu-label="pending ? (pending.question.title ?? pending.question.message) : undefined"
    :class-names="{ menu: pending ? 'w-72' : menuClass }"
  >
    <template #activator="{ attrs }">
      <slot
        name="activator"
        :attrs="attrs"
      />
    </template>
    <div
      @click.capture="startClick()"
      @click="endClick($event)"
    >
      <InlineConfirm
        v-if="pending"
        layout="panel"
        :question="pending.question"
        @cancel="cancel()"
        @confirm="accept()"
      />
      <div
        v-show="!pending"
        ref="entries"
        data-testid="confirm-menu-entries"
      >
        <slot :ask="ask" />
      </div>
    </div>
  </RuiMenu>
</template>
