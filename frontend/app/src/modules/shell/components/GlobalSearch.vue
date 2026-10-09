<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import GlobalSearchFooter from '@/modules/shell/components/GlobalSearchFooter.vue';
import GlobalSearchItemTexts from '@/modules/shell/components/GlobalSearchItemTexts.vue';
import { type SearchItem, useGlobalSearch } from '@/modules/shell/layout/use-global-search';

const { isMini = false } = defineProps<{
  isMini?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { assetSearchError, search: performSearch } = useGlobalSearch();
const router = useRouter();
const interop = useInterop();

const open = ref<boolean>(false);
const isMac = ref<boolean>(false);
const input = useTemplateRef<any>('input');
const selected = ref<number>();
const search = ref<string>('');
const loading = ref<boolean>(false);
const visibleItems = ref<SearchItem[]>([]);

const key = '/';

/** The shortcut as the platform writes it: Command on macOS, Control elsewhere. */
const shortcutLabel = computed<string>(() => `${get(isMac) ? '⌘' : 'Ctrl'} ${key}`);

function change(index?: number): void {
  if (!isDefined(index))
    return;

  const item = get(visibleItems)[index];
  if (item) {
    // Resolve to a fullPath so the "already here" guard works for both string and named-location routes.
    if (item.route && get(router.currentRoute).fullPath !== router.resolve(item.route).fullPath)
      startPromise(router.push(item.route));

    item.action?.();
    set(open, false);
  }
}

watchDebounced(search, async (keyword) => {
  set(visibleItems, await performSearch(keyword));
  set(loading, false);
}, { debounce: 800 });

watch(search, (value) => {
  set(loading, !!value);
});

watch(open, (isOpen) => {
  nextTick(() => {
    if (isOpen) {
      setTimeout(() => {
        get(input)?.focus?.();
      }, 100);
    }
    set(selected, undefined);
    set(search, '');
  });
});

/**
 * Whether this keystroke is the search shortcut on the platform the app is running on.
 *
 * @remarks
 * macOS puts the shortcut on Command and every other platform on Control, and the check is one way
 * round rather than accepting either, so the wrong modifier does not open the palette.
 */
function isSearchShortcut(event: KeyboardEvent): boolean {
  const modifier = get(isMac) ? event.metaKey : event.ctrlKey;
  return modifier && event.key === key;
}

onBeforeMount(async () => {
  set(isMac, await interop.isMac());

  window.addEventListener('keydown', (event) => {
    if (isSearchShortcut(event))
      set(open, true);
  });
});
</script>

<template>
  <!-- a command palette sits high, near where the eye already is, rather than centred -->
  <RuiDialog
    v-model="open"
    max-width="720"
    :class-names="{ content: 'top-[12vh] translate-y-0' }"
  >
    <template #activator="{ attrs }">
      <div
        class="transition-all"
        :class="isMini ? 'pl-1' : 'px-3 py-2'"
      >
        <div
          v-if="!isMini"
          class="flex items-center gap-2 rounded-rui-control px-3 h-9 bg-rui-surface-muted border border-rui-divider hover:border-rui-outline text-rui-text-secondary text-sm cursor-pointer transition-colors"
          role="button"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-search"
            size="16"
          />
          <span class="flex-1">{{ t('common.actions.search') }}</span>
          <kbd class="inline-flex items-center gap-0.5 rounded-rui-sm border border-rui-divider bg-rui-surface px-1.5 h-5 text-xs font-sans text-rui-text-secondary">
            {{ shortcutLabel }}
          </kbd>
        </div>
        <RuiButton
          v-else
          variant="text"
          icon
          class="mb-3"
          :aria-label="t('common.actions.search')"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-search"
            size="18"
          />
        </RuiButton>
      </div>
    </template>
    <RuiCard
      variant="flat"
      no-padding
      :class-names="{ content: 'overflow-hidden' }"
    >
      <RuiAutoComplete
        ref="input"
        v-model="selected"
        v-model:search-input="search"
        no-filter
        :no-data-text="t('global_search.no_actions')"
        hide-details
        :loading="loading"
        :item-height="44"
        :options="visibleItems"
        text-attr="text"
        key-attr="value"
        :label="t('common.actions.search')"
        label-placement="hidden"
        prepend-icon="lu-search"
        hide-arrow
        auto-select-first
        :placeholder="t('global_search.search_placeholder')"
        @update:model-value="change($event)"
      >
        <template #selection>
          <span />
        </template>
        <template #item="{ item }">
          <div class="flex items-center gap-3 text-sm w-full min-w-0">
            <div class="size-6 shrink-0 flex items-center justify-center text-rui-text-secondary">
              <AssetIcon
                v-if="item.asset"
                size="24px"
                :identifier="item.asset"
              />
              <LocationIcon
                v-else-if="item.location"
                icon
                size="20px"
                :item="item.location.identifier"
              />
              <AppImage
                v-else-if="item.image"
                class="icon-bg"
                :src="item.image"
                fit="contain"
                size="20px"
              />
              <RuiIcon
                v-else-if="item.icon"
                :name="item.icon"
                size="20"
              />
            </div>
            <GlobalSearchItemTexts
              :texts="item.texts"
              :text="item.text"
            />
            <div
              v-if="item.price || item.total"
              class="ms-auto shrink-0 flex items-center gap-4 text-right"
            >
              <div v-if="item.price">
                <div class="text-xs text-rui-text-secondary">
                  {{ t('common.price') }}
                </div>
                <FiatDisplay
                  :price-asset="item.asset"
                  :value="item.price"
                  class="font-medium"
                />
              </div>
              <div v-if="item.total">
                <div class="text-xs text-rui-text-secondary">
                  {{ t('common.total') }}
                </div>
                <FiatDisplay
                  :value="item.total"
                  class="font-medium"
                />
              </div>
            </div>
          </div>
        </template>
        <!-- In the dropdown's footer: below the input the open dropdown would cover it. -->
        <template #footer>
          <GlobalSearchFooter :asset-search-error="assetSearchError" />
        </template>
      </RuiAutoComplete>
    </RuiCard>
  </RuiDialog>
</template>
