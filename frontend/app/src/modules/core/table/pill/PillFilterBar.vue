<script setup lang="ts">
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { NarrowSuggestion } from '@/modules/core/table/pill/core/narrowing';
import type { ActiveFilter, FieldDef, PillBarLabels } from '@/modules/core/table/pill/core/types';
import { useFilterState } from '@/modules/core/table/pill/composables/use-filter-state';
import { useNarrowSuggestions } from '@/modules/core/table/pill/composables/use-narrow-suggestions';
import { useRecentFilterValues } from '@/modules/core/table/pill/composables/use-recent-filter-values';
import { hasWritableValue } from '@/modules/core/table/pill/core/codec';
import { resolveEditor } from '@/modules/core/table/pill/core/field-adapter';
import { narrowActiveId } from '@/modules/core/table/pill/core/narrow-ids';
import { defaultOp } from '@/modules/core/table/pill/core/operators';
import FilterPill from '@/modules/core/table/pill/FilterPill.vue';
import PillMenu from '@/modules/core/table/pill/PillMenu.vue';
import PillNarrowList from '@/modules/core/table/pill/PillNarrowList.vue';
import PillValueEditor from '@/modules/core/table/pill/PillValueEditor.vue';

const matches = defineModel<MatchedKeywordWithBehaviour<string>>('matches', { default: () => ({}) });
const params = defineModel<Record<string, string | string[] | boolean>>('params', { default: () => ({}) });

const { fields, disabled = false, labels } = defineProps<{
  fields: FieldDef[];
  labels: PillBarLabels;
  disabled?: boolean;
}>();

defineSlots<{
  /**
   * Per-table controls that modify how the active filters apply rather than filtering anything
   * themselves. Rendered inside the bar, and only while at least one filter is active — a
   * modifier with nothing to modify is a control that does nothing.
   *
   * Generic on purpose: the bar knows only that such controls may exist, never what any of them
   * mean. History fills this with "match exact events"; another table's modifier goes here the
   * same way, with no change to the bar.
   */
  modifiers?: (props: { disabled: boolean }) => any;
  /**
   * Saved filter sets for this table. Always rendered, unlike `modifiers`: the whole point of a
   * stored view is to be reachable from an empty bar, which is exactly when there are no filters.
   *
   * Filled per table rather than owned by the bar, because a view is stored per table (its
   * `SavedFilterLocation`) and applying one means writing the table's own filter models.
   */
  views?: (props: { disabled: boolean }) => any;
}>();

const model = useFilterState(() => fields);
const { remember } = useRecentFilterValues();
const addMenuOpen = ref<boolean>(false);
/** Key of the pill whose value editor is open, at most one at a time. */
const openEditorKey = ref<string>();
/** The inline narrow input, which searches across every field at once rather than one picked field. */
const query = ref<string>('');
const narrowOpen = ref<boolean>(false);
const highlighted = ref<number>(0);
const narrowInput = useTemplateRef<HTMLInputElement>('narrowInput');
/** Set while the open editor teleports something outside its popover, which would read as a click away. */
const editorPersistent = ref<boolean>(false);

const fieldByKey = computed<Map<string, FieldDef>>(() => new Map(fields.map(field => [field.key, field])));

const activeFilters = computed<{ field: FieldDef; filter: ActiveFilter }[]>(() =>
  get(model.state)
    .map(filter => ({ field: get(fieldByKey).get(filter.fieldKey), filter }))
    .filter((entry): entry is { field: FieldDef; filter: ActiveFilter } => entry.field !== undefined),
);

const availableFields = computed<FieldDef[]>(() => {
  const used = new Set(get(model.state).map(filter => filter.fieldKey));
  // Fields an active filter rules out: two fields writing the same wire keys cannot both be set.
  const excluded = new Set(
    get(activeFilters).flatMap(({ field }) => field.excludes ?? []),
  );
  return fields.filter(field => !used.has(field.key) && !excluded.has(field.key));
});

const { examples: syntaxExamples, loading: searching, suggestions } = useNarrowSuggestions(query, availableFields);

// external wire form <-> model (the model's self-echo guard breaks the round-trip loop)
watchImmediate(matches, value => model.setFromMatches(value, get(params)));
watch(params, value => model.setFromMatches(get(matches), value));
watch([model.matches, model.params], ([nextMatches, nextParams]) => {
  set(matches, nextMatches);
  set(params, nextParams);
});

// Keyed on the query, not the suggestions: late asset results must not move the row Enter is aimed at.
watch(query, () => set(highlighted, 0));

/**
 * Fields whose pill was just dropped, until the render that drops it has finished.
 *
 * The editors that debounce commit whatever they hold when they unmount, and that unmount happens
 * a render after the pill is removed: without this, removing a pill mid-edit put it straight back,
 * holding either the value being typed or nothing at all.
 */
const dropping = new Set<string>();

function hasEditor(field: FieldDef): boolean {
  return resolveEditor(field) !== 'boolean';
}

/**
 * Opens or closes a field's editor, dropping the pill when it closes with nothing in it.
 *
 * @remarks
 * An empty pill filters nothing, says nothing, and can only be got rid of by finding its remove
 * button, so picking a field and then thinking better of it must leave nothing behind.
 *
 * The close path waits a tick before deciding anything. A debounced editor commits what it holds
 * as it unmounts, on the render this call triggers, so reading the filter any earlier sees it as
 * it was before the last keystroke and throws away a half-typed range.
 *
 * A value is remembered on close, never on each update: a free-text editor commits through that
 * same debounce, so remembering every one stores `swap`, `swap on`, … as separate values and
 * rewrites the whole settings blob for each.
 */
function setEditorOpen(field: FieldDef, open: boolean): void {
  set(openEditorKey, open ? field.key : undefined);
  set(editorPersistent, false);
  if (open)
    return;

  nextTick(() => {
    const filter = get(model.state).find(entry => entry.fieldKey === field.key);
    if (!filter) {
      focusBar();
      return;
    }

    if (!hasWritableValue(field, filter)) {
      dropFilter(field);
      return;
    }

    remember(field, filter.values);
    focusBar();
  });
}

/**
 * Puts the caret back in the bar's input.
 *
 * `RuiMenu` returns focus to its activator when it closes, but only when `disable-auto-focus` is
 * off — and every editor here sets it, because without it the menu takes focus off the input the
 * moment it opens and typing becomes impossible. The one prop governs both directions, so opting
 * out of the first opts out of the second, and focus is left on the document body: the editor that
 * held it has unmounted and the pill it belonged to may be gone too.
 */
function focusBar(): void {
  get(narrowInput)?.focus();
}

/**
 * Removes a pill and puts the caret back in the bar's input. Whatever held focus went with the
 * pill, so without this focus falls back to the document body and the next keystroke goes nowhere:
 * the bar is where the user still is, and typing is how they carry on.
 */
function dropFilter(field: FieldDef): void {
  dropping.add(field.key);
  model.removeFilter(field.key);
  nextTick(() => {
    dropping.delete(field.key);
    focusBar();
  });
}

function addField(field: FieldDef): void {
  set(addMenuOpen, false);
  // A boolean field is on once added, so only fields with an editor get one opened for them.
  model.addFilter({ fieldKey: field.key, op: defaultOp(field), values: [] });
  if (hasEditor(field))
    nextTick(() => set(openEditorKey, field.key));
}

function updateFilter(filter: ActiveFilter): void {
  if (dropping.has(filter.fieldKey))
    return;
  model.addFilter(filter); // replaces the filter for this field
}

/**
 * Drops a field's pill, clearing the open-editor key first when that pill owned it.
 *
 * @remarks
 * `openEditorKey` is set by `addField` on the next tick, so a stale key left pointing at this field
 * would make re-adding it a no-op change and its editor would never reopen.
 */
function removeFilter(field: FieldDef): void {
  if (get(openEditorKey) === field.key)
    set(openEditorKey, undefined);
  dropFilter(field);
}

function clearAll(): void {
  set(openEditorKey, undefined);
  model.clearAll();
  // The button that was just pressed is rendered only while filters exist, so it goes with them.
  nextTick(() => focusBar());
}

/**
 * Applying a filter clears what was typed but deliberately leaves the popover open, so several
 * filters can be added in a row without clicking back into the bar. Escape is the way out.
 */
function clearQuery(): void {
  set(query, '');
}

/**
 * A field suggestion behaves like picking it from the `+ Add filter` menu (empty pill, editor
 * opens): the popover closes, since its editor takes over and two stacked popovers would be
 * wrong. A value suggestion is the whole point of the inline input: it applies the filter in one
 * step, so typing `eth` and pressing Enter is a complete action, and the popover stays open for
 * the next one. A filter suggestion is the same thing for a written value: the field already read
 * the operator and bounds out of the query, so there is nothing left to fill in.
 */
function applySuggestion(suggestion: NarrowSuggestion): void {
  clearQuery();
  if (suggestion.kind === 'field') {
    set(narrowOpen, false);
    addField(suggestion.field);
    return;
  }
  if (suggestion.kind === 'filter') {
    model.addFilter(suggestion.filter);
    return;
  }
  model.addFilter({
    fieldKey: suggestion.field.key,
    op: defaultOp(suggestion.field),
    values: [suggestion.value],
  });
  remember(suggestion.field, [suggestion.value]);
}

/**
 * A footer example was clicked: it goes into the input, it is not applied.
 *
 * The footer exists to teach a syntax nothing else on screen mentions, and watching the text land
 * in the bar and turn into a filter row is the lesson. Applying it outright would add a pill for a
 * date the user has no interest in and teach them only that the footer is a set of odd shortcuts.
 * The caret goes back to the input so the obvious next move, editing the date, just works.
 */
function applyExample(example: string): void {
  set(query, example);
  set(narrowOpen, true);
  get(narrowInput)?.focus();
}

// Rows and footer chips form one arrow-navigable sequence, chips last: the teleported popover takes no Tab.
const navigableCount = computed<number>(() => get(suggestions).length + get(syntaxExamples).length);

const activeSuggestionId = computed<string | undefined>(() => {
  if (!get(narrowOpen) || get(navigableCount) === 0)
    return undefined;

  return narrowActiveId(get(highlighted), get(suggestions).length);
});

function moveHighlight(step: number): void {
  const count = get(navigableCount);
  if (count > 0)
    set(highlighted, (get(highlighted) + step + count) % count);
}

/** What Enter does to whatever the highlight is on, row or footer chip. */
function applyHighlighted(items: NarrowSuggestion[]): void {
  const index = get(highlighted);
  // Past the last row is a footer chip, which only writes its example into the input.
  const example = get(syntaxExamples)[index - items.length];
  if (example !== undefined) {
    applyExample(example);
    return;
  }
  // The list can shrink under the highlight (a search returning less than the last one).
  applySuggestion(items[index] ?? items[0]);
}

function onNarrowKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    clearQuery();
    set(narrowOpen, false);
    return;
  }

  // An empty input plus Backspace drops the last pill, the usual token-field shortcut.
  if (event.key === 'Backspace' && !get(query)) {
    const last = get(activeFilters).at(-1);
    if (last)
      removeFilter(last.field);
    return;
  }

  const items = get(suggestions);
  if (get(navigableCount) === 0)
    return;

  if (event.key === 'ArrowDown') {
    event.preventDefault();
    moveHighlight(1);
  }
  else if (event.key === 'ArrowUp') {
    event.preventDefault();
    moveHighlight(-1);
  }
  else if (event.key === 'Enter') {
    event.preventDefault();
    applyHighlighted(items);
  }
}

/**
 * Makes a click anywhere on the bar behave like a click on its input.
 *
 * @remarks
 * Checking `target !== currentTarget` is not enough: most of the bar's dead space belongs to the
 * wrapper around the input rather than the bar itself, so the middle would do nothing.
 *
 * The suggestions are opened as well as focused. The input is the menu's activator, so clicking it
 * opens them; the dead space is not, so without this the two halves of one bar behave differently
 * depending on how far along it the user happens to click.
 */
function focusInput(event: MouseEvent): void {
  const { target } = event;
  if (disabled || (target instanceof Element && target.closest('button, a, input, [data-testid=filter-pill]')))
    return;

  get(narrowInput)?.focus();
  set(narrowOpen, true);
}
</script>

<template>
  <!-- py-1 rather than py-1.5: the bar sits next to buttons on most of its screens, and at 43px it
       was the tallest control in every one of those rows. -->
  <div
    class="flex flex-wrap items-center gap-1.5 px-2 py-1 rounded-md border transition-colors border-rui-grey-300 dark:border-rui-grey-700 focus-within:border-rui-primary dark:focus-within:border-rui-primary"
    :class="{ 'opacity-50': disabled }"
    data-testid="pill-bar"
    @click="focusInput($event)"
  >
    <RuiMenu
      v-for="entry in activeFilters"
      :key="entry.filter.fieldKey"
      :model-value="openEditorKey === entry.filter.fieldKey"
      :disabled="disabled || !hasEditor(entry.field)"
      :persistent="editorPersistent && openEditorKey === entry.filter.fieldKey"
      :options="{ placement: 'bottom-start' }"
      disable-auto-focus
      @update:model-value="setEditorOpen(entry.field, $event)"
    >
      <template #activator="{ attrs }">
        <FilterPill
          v-bind="attrs"
          :field="entry.field"
          :filter="entry.filter"
          :disabled="disabled"
          :remove-label="labels.remove"
          @remove="removeFilter(entry.field)"
        />
      </template>
      <PillValueEditor
        v-if="hasEditor(entry.field)"
        :field="entry.field"
        :filter="entry.filter"
        @update="updateFilter($event)"
        @close="setEditorOpen(entry.field, false)"
        @persist="editorPersistent = $event"
      />
    </RuiMenu>

    <!-- The caret has to stay in the input while the popover is open: the menu must not pull
         focus into its content (`disable-auto-focus`), must not close when the input that opened
         it is clicked again, and must stay open when a suggestion is picked, so filters can be
         added in a row the same way by mouse as by keyboard.

         `bottom-start` because the menu's default placement centres it on the activator, and the
         activator here is the full-width input: the list would hang half a bar-width to the left
         of the text the user is typing. Every popover in the bar drops from the left edge of what
         opened it.

         `full-width` because the menu's activator wrapper is `inline-flex`, so it shrinks to the
         input's intrinsic size and the `flex-1` on the menu itself only grows the box around it:
         the input has to fill whatever the pills leave on the line, not sit at its default width. -->
    <RuiMenu
      v-model="narrowOpen"
      :disabled="disabled"
      :close-on-content-click="false"
      :options="{ placement: 'bottom-start' }"
      disable-auto-focus
      persist-on-activator-click
      full-width
      class="flex-1 min-w-[8rem]"
    >
      <template #activator="{ attrs }">
        <div
          v-bind="attrs"
          class="flex-1 min-w-[8rem]"
        >
          <input
            ref="narrowInput"
            v-model="query"
            type="text"
            aria-haspopup="menu"
            aria-controls="pill-narrow-list"
            :aria-expanded="narrowOpen"
            :aria-activedescendant="activeSuggestionId"
            :aria-label="labels.narrow"
            :placeholder="labels.narrow"
            :disabled="disabled"
            autocomplete="off"
            spellcheck="false"
            class="w-full min-w-0 bg-transparent py-1 text-sm text-rui-text-primary outline-none placeholder:text-rui-text-secondary"
            data-testid="pill-narrow-input"
            @input="narrowOpen = true"
            @keydown="onNarrowKeydown($event)"
          />
        </div>
      </template>
      <PillNarrowList
        id="pill-narrow-list"
        :suggestions="suggestions"
        :loading="searching"
        :highlighted="highlighted"
        :empty-text="labels.narrowEmpty"
        :examples="syntaxExamples"
        :examples-label="labels.syntax"
        @example="applyExample($event)"
        @select="applySuggestion($event)"
        @update:highlighted="highlighted = $event"
      />
    </RuiMenu>

    <!-- Not pills: a pill is a predicate, and these only constrain how the predicates apply. See
         the slot's declaration for why it is gated on there being filters at all. -->
    <slot
      v-if="activeFilters.length > 0"
      name="modifiers"
      :disabled="disabled"
    />

    <slot
      name="views"
      :disabled="disabled"
    />

    <!-- `flex` on the menu root: its activator wrapper is `inline-flex`, so in a block root it sits
         on the text baseline and the descender makes this one child a pixel taller than the button
         inside it, which reads as "Add filter" and "Clear all" being off by a pixel. -->
    <RuiMenu
      v-model="addMenuOpen"
      :disabled="disabled || availableFields.length === 0"
      :options="{ placement: 'bottom-start' }"
      class="flex"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="attrs"
          variant="text"
          size="sm"
          :disabled="disabled || availableFields.length === 0"
          data-testid="pill-add"
        >
          <template #prepend>
            <RuiIcon
              name="lu-plus"
              size="16"
            />
          </template>
          {{ labels.add }}
        </RuiButton>
      </template>
      <PillMenu
        :fields="availableFields"
        :search-placeholder="labels.search"
        :empty-text="labels.empty"
        @select="addField($event)"
      />
    </RuiMenu>

    <RuiButton
      v-if="activeFilters.length > 0"
      variant="text"
      size="sm"
      :disabled="disabled"
      data-testid="pill-clear"
      @click="clearAll()"
    >
      {{ labels.clear }}
    </RuiButton>
  </div>
</template>
