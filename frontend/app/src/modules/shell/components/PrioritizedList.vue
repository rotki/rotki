<script setup lang="ts">
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import type { PrioritizedListData, PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import { assert, type Nullable, pluralize } from '@rotki/common';
import { EmptyListId, type PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import PrioritizedListEntry from '@/modules/shell/components/PrioritizedListEntry.vue';
import PrioritizedListRow from '@/modules/shell/components/PrioritizedListRow.vue';

const modelValue = defineModel<PrioritizedListId[]>({ required: true });

const {
  allItems,
  dense,
  disableAdd,
  disableDelete,
  itemDataName = '',
  status,
  emptyWarning,
  variant = 'outlined',
} = defineProps<{
  allItems: PrioritizedListData<PrioritizedListId>;
  itemDataName?: string;
  disableAdd?: boolean;
  disableDelete?: boolean;
  dense?: boolean;
  /** The outcome of the last save, shown in a slot that is always reserved so nothing moves. */
  status?: BaseMessage;
  /** Shown inside the list, as a warning, when it is empty, for a list that must not be. */
  emptyWarning?: string;
  variant?: 'flat' | 'outlined';
}>();

defineSlots<{
  default: () => any;
  title: () => any;
  /** Replaces the default success text, for a status that carries an action. */
  status?: () => any;
}>();

const [DefineStatus, ReuseStatus] = createReusableTemplate();
// an error can run to several lines and stays until acted on, so it gets a full-width block of its own
const [DefineError, ReuseError] = createReusableTemplate();

/** The error the user closed; it stays hidden until a different one arrives. */
const dismissedError = ref<string>('');

const shownError = computed<string>(() => {
  const error = status?.error ?? '';
  return error === get(dismissedError) ? '' : error;
});

// a cleared error means a new attempt, whose failure should show even with the same wording
watch(() => status?.error, (error) => {
  if (!error)
    set(dismissedError, '');
});

const selection = ref<Nullable<PrioritizedListId>>(null);

const input = (items: PrioritizedListId[]): void => set(modelValue, items);

const itemNameTr = computed(() => ({
  name: itemDataName,
  namePluralized: pluralize(itemDataName, 2),
}));

const missing = computed<PrioritizedListId[]>(() => allItems.itemIdsNotIn(get(modelValue)));

const noResults = computed<boolean>(() => get(modelValue).length === 0);

const isFirst = (item: string): boolean => get(modelValue)[0] === item;

function isLast(item: string): boolean {
  const items = get(modelValue);
  return items.at(-1) === item;
}

function itemData(identifier: PrioritizedListId): PrioritizedListItemData<PrioritizedListId> {
  return allItems.itemDataForId(identifier) ?? { identifier: EmptyListId };
}

function addItem(): void {
  assert(get(selection));
  const items = [...get(modelValue)];
  items.push(get(selection)!);
  input(items);
  set(selection, null);
}

function move(item: PrioritizedListId, down: boolean): void {
  const items = [...get(modelValue)];
  const itemIndex = items.indexOf(item);
  const nextIndex = itemIndex + (down ? 1 : -1);
  const nextItem = items[nextIndex];
  items[nextIndex] = item;
  items[itemIndex] = nextItem;
  input(items);
}

function remove(item: PrioritizedListId): void {
  const items = [...get(modelValue)];
  const itemIndex = items.indexOf(item);
  items.splice(itemIndex, 1);
  input(items);
}

const { t } = useI18n({ useScope: 'global' });

const autoCompleteHint = computed<string>(() => {
  const num = get(missing).length;
  if (num) {
    return t('prioritized_list.disabled_items', {
      namePluralized: get(itemNameTr).namePluralized,
      num,
    });
  }
  return t('prioritized_list.all_added', get(itemNameTr));
});
</script>

<template>
  <div class="flex flex-col gap-2 pb-1">
    <DefineStatus>
      <Transition
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
        enter-active-class="transition-opacity duration-200"
        leave-active-class="transition-opacity duration-500"
        mode="out-in"
      >
        <span
          v-if="status?.success && !status.error"
          key="success"
          class="flex items-center gap-1 text-xs font-normal text-rui-success"
          role="status"
          data-testid="prioritized-list-status"
        >
          <RuiIcon
            name="lu-check"
            size="14"
            class="shrink-0"
          />
          <slot name="status">
            {{ status.success }}
          </slot>
        </span>
      </Transition>
    </DefineStatus>

    <DefineError>
      <div
        v-if="shownError"
        class="flex items-start gap-2 rounded-rui-control bg-rui-error/10 pl-3 pr-1 py-1 text-xs leading-5 text-rui-error"
        role="alert"
        data-testid="prioritized-list-status"
      >
        <RuiIcon
          name="lu-circle-alert"
          size="14"
          class="shrink-0 mt-1.75"
        />
        <span class="flex-1 py-1">{{ shownError }}</span>
        <RuiButton
          variant="text"
          icon
          size="sm"
          color="error"
          class="shrink-0"
          :aria-label="t('common.actions.dismiss')"
          data-testid="prioritized-list-dismiss"
          @click="dismissedError = shownError"
        >
          <RuiIcon
            name="lu-x"
            size="14"
          />
        </RuiButton>
      </div>
    </DefineError>

    <RuiCard
      rounded="md"
      no-padding
      :variant="variant"
      class="overflow-hidden"
      :class="{ '[&>div:first-child]:px-6 [&>div:first-child]:pb-2': $slots.title || variant === 'flat' }"
    >
      <template
        v-if="$slots.title"
        #header
      >
        <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <slot name="title" />
          <ReuseStatus />
        </div>
      </template>

      <div
        v-if="$slots.title && shownError"
        class="px-6 pb-3"
      >
        <ReuseError />
      </div>

      <div
        v-if="!disableAdd"
        class="flex pb-2 gap-2 items-start border-b border-default overflow-hidden"
        :class="variant === 'outlined' ? 'px-6' : 'px-px'"
      >
        <RuiAutoComplete
          v-model="selection"
          dense
          class="overflow-hidden py-1.5"
          :label="t('prioritized_list.add_placeholder', itemNameTr)"
          label-placement="hidden"
          :placeholder="t('prioritized_list.add_placeholder', itemNameTr)"
          :no-data-text="t('prioritized_list.all_added', itemNameTr)"
          :options="missing"
          :item-height="36"
          :hint="autoCompleteHint"
        >
          <template #selection="{ item }">
            <PrioritizedListEntry
              :data="itemData(item)"
              size="24px"
            />
          </template>
          <template #item="{ item }">
            <PrioritizedListEntry
              :data="itemData(item)"
              size="24px"
            />
          </template>
        </RuiAutoComplete>
        <RuiButton
          id="add-item-btn"
          color="primary"
          variant="outlined"
          size="sm"
          :disabled="!selection"
          class="h-8 mt-1.5"
          @click="addItem()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-plus"
              size="16"
            />
          </template>
          {{ t('common.actions.add') }}
        </RuiButton>
      </div>
      <div
        v-if="noResults && emptyWarning"
        class="flex items-center gap-2 px-6 py-4 text-sm text-rui-warning"
        role="alert"
        data-testid="prioritized-list-empty-warning"
      >
        <RuiIcon
          name="lu-triangle-alert"
          size="16"
          class="shrink-0"
        />
        {{ emptyWarning }}
      </div>
      <RuiTable
        v-else
        variant="default"
        :empty="noResults ? { label: t('prioritized_list.item.empty', itemNameTr) } : false"
      >
        <thead>
          <tr>
            <th class="w-10 text-center">
              {{ t('common.priority') }}
            </th>
            <th class="pl-0">
              {{ t('common.name') }}
            </th>
            <th class="pl-0" />
          </tr>
        </thead>
        <TransitionGroup
          move-class="transition-all"
          tag="tbody"
        >
          <PrioritizedListRow
            v-for="(identifier, index) in modelValue"
            :key="identifier"
            :item="{
              identifier,
              index,
              data: itemData(identifier),
              first: isFirst(identifier),
              last: isLast(identifier),
            }"
            :dense="dense"
            :disable-delete="disableDelete"
            :delete-label="t('prioritized_list.item.delete', itemNameTr)"
            @move="move(identifier, $event)"
            @remove="remove(identifier)"
          />
        </TransitionGroup>
      </RuiTable>
    </RuiCard>
    <div
      v-if="status && !$slots.title"
      class="min-h-5 mx-px"
    >
      <ReuseError />
      <ReuseStatus />
    </div>
  </div>
</template>
