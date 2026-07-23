<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import GlobalSearchItemTexts from '@/modules/shell/components/GlobalSearchItemTexts.vue';
import { type SearchItem, useGlobalSearch } from '@/modules/shell/layout/use-global-search';

const { isMini = false } = defineProps<{
  isMini?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { search: performSearch } = useGlobalSearch();
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

onBeforeMount(async () => {
  set(isMac, await interop.isMac());

  window.addEventListener('keydown', (event) => {
    // Mac uses Command, others use Control
    if (((get(isMac) && event.metaKey) || (!get(isMac) && event.ctrlKey)) && event.key === key)
      set(open, true);
  });
});
</script>

<template>
  <RuiDialog
    v-model="open"
    max-width="800"
    content-class="mt-[16rem] !top-0 pb-2"
  >
    <template #activator="{ attrs }">
      <div
        class="transition-all"
        :class="isMini ? 'pl-1' : 'px-3 py-2'"
      >
        <div
          v-if="!isMini"
          class="flex items-center gap-2 justify-between rounded-lg px-3 py-2 bg-rui-grey-100 dark:bg-rui-grey-800 cursor-pointer border border-rui-grey-300 hover:border-rui-grey-400 dark:border-rui-grey-700 dark:hover:border-rui-grey-600 text-rui-text-secondary opacity-70"
          role="button"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-search"
            size="16"
          />
          <span class="flex-1 ml-1">{{ t('common.actions.search') }}</span>
          <RuiIcon
            name="lu-command"
            size="14"
          />
          {{ key }}
        </div>
        <RuiButton
          v-else
          variant="text"
          class="p-2 w-full mb-3 border border-rui-grey-200 dark:border-rui-grey-700 !bg-rui-grey-100 hover:!bg-rui-grey-200 dark:!bg-rui-grey-800 hover:dark:!bg-rui-grey-700 rounded-lg"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-search"
            class="opacity-60"
            size="18"
          />
        </RuiButton>
      </div>
    </template>
    <RuiCard
      variant="flat"
      no-padding
      rounded="sm"
      content-class="overflow-hidden"
    >
      <RuiAutoComplete
        ref="input"
        v-model="selected"
        v-model:search-input="search"
        no-filter
        :no-data-text="t('global_search.no_actions')"
        hide-details
        :loading="loading"
        :item-height="50"
        :options="visibleItems"
        text-attr="text"
        key-attr="value"
        label=""
        auto-select-first
        :placeholder="t('global_search.search_placeholder')"
        @update:model-value="change($event)"
      >
        <template #selection>
          <span />
        </template>
        <template #item="{ item }">
          <div class="flex items-center text-body-2 w-full">
            <AssetIcon
              v-if="item.asset"
              class="-my-1"
              size="30px"
              :identifier="item.asset"
            />
            <template v-else>
              <LocationIcon
                v-if="item.location"
                icon
                size="26px"
                :item="item.location.identifier"
              />
              <AppImage
                v-else-if="item.image"
                class="icon-bg"
                :src="item.image"
                contain
                size="26px"
              />
              <RuiIcon
                v-else-if="item.icon"
                :name="item.icon"
                size="26px"
              />
            </template>
            <GlobalSearchItemTexts
              :texts="item.texts"
              :text="item.text"
            />
            <div class="grow" />
            <div
              v-if="item.price"
              class="text-right -my-6"
            >
              <div class="text-caption">
                {{ t('common.price') }}:
              </div>
              <FiatDisplay
                :price-asset="item.asset"
                :value="item.price"
                class="font-bold"
              />
            </div>
            <div
              v-if="item.total"
              class="text-right -my-4"
            >
              <div class="text-caption">
                {{ t('common.total') }}:
              </div>
              <FiatDisplay
                :value="item.total"
                class="font-bold"
              />
            </div>
          </div>
        </template>
      </RuiAutoComplete>
    </RuiCard>
  </RuiDialog>
</template>
