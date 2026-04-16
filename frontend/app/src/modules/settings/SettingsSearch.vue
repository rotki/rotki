<script setup lang="ts">
import type { SettingsSearchEntry } from '@/modules/settings/setting-highlight-ids';
import { startPromise } from '@shared/utils';
import SettingsSearchItem from '@/modules/settings/SettingsSearchItem.vue';
import { useSettingsHighlight } from '@/modules/settings/use-settings-highlight';
import { useSettingsSearch } from '@/modules/settings/use-settings-search';

interface VisibleItem extends SettingsSearchEntry {
  value: number;
  text: string;
}

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const search = ref<string>('');
const selected = ref<number>();
const visibleItems = ref<VisibleItem[]>([]);

const { requestHighlight } = useSettingsHighlight();
const { entries, filterEntries } = useSettingsSearch();

function onSelect(index?: number): void {
  if (!isDefined(index))
    return;

  const item: VisibleItem | undefined = get(visibleItems)[index];
  if (!item)
    return;

  const targetId = item.categoryId ?? item.highlightId;
  if (targetId)
    requestHighlight(targetId, item.highlightId);

  startPromise(router.push(item.route));
  set(search, '');
  set(selected, undefined);
}

function updateVisibleItems(keyword: string): void {
  const all: SettingsSearchEntry[] = get(entries);
  const results: SettingsSearchEntry[] = keyword
    ? filterEntries(all, keyword)
    : all;

  set(
    visibleItems,
    results.map((entry: SettingsSearchEntry, index: number): VisibleItem => ({
      ...entry,
      text: entry.texts.join(' > '),
      value: index,
    })),
  );
}

watchDebounced(search, (keyword: string) => {
  updateVisibleItems(keyword);
}, { debounce: 300, immediate: true });
</script>

<template>
  <RuiAutoComplete
    v-model="selected"
    v-model:search-input="search"
    no-filter
    :no-data-text="t('settings.search.no_results')"
    hide-details
    :item-height="44"
    :options="visibleItems"
    text-attr="text"
    key-attr="value"
    variant="outlined"
    dense
    auto-select-first
    :label="t('settings.search.placeholder')"
    class="max-w-[400px] w-full"
    @update:model-value="onSelect($event)"
  >
    <template #selection>
      <span />
    </template>
    <template #item="{ item }">
      <SettingsSearchItem
        :icon="item.icon"
        :texts="item.texts"
      />
    </template>
  </RuiAutoComplete>
</template>
