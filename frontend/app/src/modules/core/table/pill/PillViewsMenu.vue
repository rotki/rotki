<script setup lang="ts">
import type { SavedFilterLocation } from '@/modules/core/table/filtering';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { startPromise } from '@shared/utils';
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { type SavedViewState, useSavedViews } from '@/modules/core/table/pill/composables/use-saved-views';
import { pillStateSummary } from '@/modules/core/table/pill/core/format';

const { fields, location, state, disabled = false } = defineProps<{
  /** The table's fields, which decide how a stored view reads on its row. */
  fields: FieldDef[];
  location: SavedFilterLocation;
  /** The bar's current filter set, stored as it stands when a view is saved. */
  state: SavedViewState;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  apply: [view: SavedView];
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const name = ref<string>('');
const error = ref<string>('');
const highlighted = ref<number>(0);
const saving = ref<boolean>(false);

const list = useTemplateRef<HTMLDivElement>('list');
const rows = useTemplateRef<HTMLDivElement[]>('rows');
/**
 * The star that opens the menu, typed loosely because it is a component instance and a stubbed
 * button in a unit spec has neither an element nor a focus method.
 */
const activator = useTemplateRef<{ $el?: { focus?: () => void } }>('activator');

const { addView, deleteView, ensureConverted, views } = useSavedViews(() => location, () => fields);
const operatorLabels = useOperatorLabels();

const hasFilters = computed<boolean>(() =>
  Object.keys(state.matches).length > 0 || Object.keys(state.params).length > 0,
);

/** Each view's own line of "field: value" text, so a name is not the only thing to go by. */
const summaries = computed<string[]>(() =>
  get(views).map(view => pillStateSummary(view.matches, view.params, fields, get(operatorLabels))),
);

function reset(): void {
  set(name, '');
  set(error, '');
  set(highlighted, 0);
}

function apply(view: SavedView): void {
  set(open, false);
  emit('apply', view);
}

/**
 * Saves the current filter state as a named view.
 *
 * @remarks
 * On success focus returns to the list, which now holds the new view and is where the arrow keys
 * and Escape are handled. Leaving it on the save button strands the keyboard on a control with
 * nothing left to do.
 */
async function save(): Promise<void> {
  set(saving, true);
  const status = await addView(get(name), state);
  set(saving, false);
  if (status.success) {
    reset();
    get(list)?.focus();
    return;
  }
  set(error, status.message ?? '');
}

async function remove(index: number): Promise<void> {
  await deleteView(index);
  // The list shrank under the highlight, which would otherwise point past its end.
  set(highlighted, Math.min(get(highlighted), Math.max(get(views).length - 1, 0)));
  // The button that was just clicked is gone, so focus would otherwise fall back to the body.
  get(list)?.focus();
}

/**
 * Handles the keys the list owns, so a view can be picked without a mouse.
 *
 * @remarks
 * The menu focuses the list on open, the name field is a Tab away for saving, and Enter on a
 * highlighted row applies it. Escape is handled here rather than left to the menu: dismissal by the
 * menu depends on where focus sits, and an empty list would have nothing else to hand it to.
 */
function onListKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    set(open, false);
    return;
  }

  const count = get(views).length;
  if (count === 0)
    return;

  if (event.key === 'ArrowDown') {
    event.preventDefault();
    set(highlighted, (get(highlighted) + 1) % count);
    scrollToHighlighted();
  }
  else if (event.key === 'ArrowUp') {
    event.preventDefault();
    set(highlighted, (get(highlighted) - 1 + count) % count);
    scrollToHighlighted();
  }
  else if (event.key === 'Enter') {
    event.preventDefault();
    apply(get(views)[get(highlighted)]);
  }
}

/**
 * Starts the menu from a clean slate and migrates this table's legacy saved filters.
 *
 * @remarks
 * The conversion is tied to opening rather than to mounting: on mount the write lands in the burst
 * of settings writes that logging in fires, and because the whole frontend-settings blob is written
 * at once, a later write built from a snapshot that predates the conversion silently discards it.
 */
function onOpened(): void {
  reset();
  startPromise(ensureConverted());
}

watch(open, (isOpen: boolean): void => {
  if (isOpen)
    onOpened();
});

/**
 * Brings the highlighted row into view, scrolling as little as it takes.
 *
 * @remarks
 * Belongs to the key handler and must stay there. Driving it from a watcher on the highlight
 * would fire on hover as well, and the scroll then drags the list out from under a stationary
 * cursor, which moves the highlight again.
 */
function scrollToHighlighted(): void {
  get(rows)?.[get(highlighted)]?.scrollIntoView({ block: 'nearest' });
}

/**
 * Keeps the keyboard inside the menu: the list holds focus while it is open, and the star that
 * opened it takes focus back once it closes.
 *
 * @remarks
 * The list owns the arrow keys and Escape, so a menu that has to be reached with the mouse is not
 * keyboard-navigable, and once the list unmounts focus would otherwise fall to the document body.
 * `RuiMenu` returns focus to its activator itself, but only while `disable-auto-focus` is off, and
 * it is on here so the menu does not take focus off the list the moment it opens: the one prop
 * governs both directions.
 *
 * @param isOpen - the menu's model.
 * @param element - the list, watched alongside `isOpen` rather than read on open, because `RuiMenu`
 * mounts its content later than the model flips, so it does not exist yet at that point.
 */
function syncFocus(isOpen: boolean, element: HTMLDivElement | null): void {
  if (isOpen)
    element?.focus();
  else
    get(activator)?.$el?.focus?.();
}

watch([open, list], ([isOpen, element]: [boolean, HTMLDivElement | null]): void => {
  syncFocus(isOpen, element);
});
</script>

<template>
  <RuiMenu
    v-model="open"
    :disabled="disabled"
    :close-on-content-click="false"
    :options="{ placement: 'bottom-start' }"
    disable-auto-focus
  >
    <!-- An icon rather than a labelled button: it sits inside the bar, where the pills are what
         should be read, and the same reasoning as the match-exact toggle applies. The tooltip
         carries the name. -->
    <template #activator="{ attrs }">
      <RuiTooltip
        :open-delay="400"
        :disabled="disabled"
      >
        <template #activator>
          <RuiButton
            v-bind="attrs"
            ref="activator"
            variant="text"
            size="sm"
            icon
            class="shrink-0"
            :disabled="disabled"
            :aria-label="t('table_filter.saved_views.title')"
            data-testid="pill-views"
          >
            <RuiIcon
              name="lu-star"
              size="18"
            />
          </RuiButton>
        </template>
        {{ t('table_filter.saved_views.title') }}
      </RuiTooltip>
    </template>

    <div class="flex flex-col min-w-[18rem] max-w-[24rem]">
      <div
        ref="list"
        tabindex="0"
        class="flex flex-col gap-0.5 p-1.5 max-h-[17rem] overflow-y-auto outline-none rounded-md focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-rui-primary"
        data-testid="pill-views-list"
        @keydown="onListKeydown($event)"
      >
        <div
          v-for="(view, index) in views"
          :key="view.name"
          ref="rows"
          class="flex items-center gap-1 rounded-md transition-colors"
          :class="index === highlighted ? 'bg-rui-primary/10' : 'hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800'"
          @mousemove="highlighted = index"
        >
          <button
            type="button"
            class="flex flex-col items-start flex-1 min-w-0 px-2.5 py-1.5 text-left"
            :title="t('table_filter.saved_views.actions.apply')"
            data-testid="pill-views-apply"
            :data-index="index"
            @click="apply(view)"
          >
            <span
              class="text-sm truncate max-w-full"
              :class="index === highlighted ? 'text-rui-primary' : 'text-rui-text-primary'"
            >
              {{ view.name }}
            </span>
            <!-- Two lines and the full text on hover: a view worth saving is usually one with
                 several filters, which is exactly the summary that a single truncated line cuts
                 off, leaving the saved views indistinguishable from one another. -->
            <span
              v-if="summaries[index]"
              class="text-xs text-rui-text-secondary line-clamp-2 max-w-full"
              :title="summaries[index]"
            >
              {{ summaries[index] }}
            </span>
          </button>
          <RuiButton
            variant="text"
            size="sm"
            icon
            class="shrink-0 mr-1"
            :aria-label="t('table_filter.saved_views.actions.remove')"
            data-testid="pill-views-delete"
            :data-index="index"
            @click="remove(index)"
          >
            <RuiIcon
              name="lu-x"
              size="16"
              class="text-rui-text-secondary"
            />
          </RuiButton>
        </div>

        <div
          v-if="views.length === 0"
          class="text-rui-text-secondary text-sm px-2.5 py-3"
          data-testid="pill-views-empty"
        >
          {{ t('table_filter.saved_views.empty') }}
        </div>
      </div>

      <div class="flex flex-col gap-1.5 p-1.5 border-t border-rui-grey-200 dark:border-rui-grey-700">
        <!-- A visible border, not a transparent one that only appears on focus: this is the only
             place in the menu you can type, and without an outline it reads as a label. -->
        <div class="flex items-center gap-1.5 rounded-md border transition-colors border-rui-grey-300 dark:border-rui-grey-700 focus-within:border-rui-primary dark:focus-within:border-rui-primary">
          <input
            v-model="name"
            type="text"
            :disabled="!hasFilters || saving"
            :placeholder="t('table_filter.saved_views.name_placeholder')"
            :aria-label="t('table_filter.saved_views.name_placeholder')"
            autocomplete="off"
            class="flex-1 min-w-0 bg-transparent px-1.5 py-1 text-sm text-rui-text-primary outline-none placeholder:text-rui-text-secondary disabled:text-rui-text-disabled"
            data-testid="pill-views-name"
            @keydown.enter.prevent="save()"
            @keydown.escape="open = false"
          />
          <RuiButton
            variant="text"
            size="sm"
            color="primary"
            :disabled="!hasFilters || !name.trim() || saving"
            data-testid="pill-views-save"
            @click="save()"
          >
            {{ t('table_filter.saved_views.actions.save') }}
          </RuiButton>
        </div>

        <!-- Says why saving is unavailable rather than leaving a dead input: there is nothing to
             save until something is filtered. -->
        <div
          v-if="!hasFilters"
          class="text-xs text-rui-text-secondary px-1.5"
          data-testid="pill-views-hint"
        >
          {{ t('table_filter.saved_views.nothing_to_save') }}
        </div>
        <div
          v-else-if="error"
          class="text-xs text-rui-error px-1.5"
          data-testid="pill-views-error"
        >
          {{ error }}
        </div>
      </div>
    </div>
  </RuiMenu>
</template>
