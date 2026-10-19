<script setup lang="ts">
import type { StakingLocation } from '@/pages/staking/staking-pages';
import AppImage from '@/modules/shell/components/AppImage.vue';
import BreadcrumbSwitchButton from '@/modules/shell/components/BreadcrumbSwitchButton.vue';
import { type StakingInfo, useStakingLocations } from '@/pages/staking/use-staking-locations';

const { location } = defineProps<{
  location: StakingLocation;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const open = ref<boolean>(false);
const search = ref<string>('');

const { getRedirectLink, overviewLink, staking } = useStakingLocations();

const current = computed<StakingInfo | undefined>(() => get(staking).find(item => item.id === location));

const filtered = computed<StakingInfo[]>(() => {
  const query = get(search).trim().toLocaleLowerCase();
  if (!query)
    return get(staking);
  return get(staking).filter(item => item.name.toLocaleLowerCase().includes(query));
});

async function pick(item: StakingInfo): Promise<void> {
  set(open, false);
  if (item.id !== location)
    await router.push(getRedirectLink(item.id));
}

/** Enter opens the only, or first, match, so a few letters and Enter switch location. */
async function pickFirst(): Promise<void> {
  const [first] = get(filtered);
  if (first)
    await pick(first);
}

watch(open, (isOpen) => {
  if (!isOpen)
    set(search, '');
});
</script>

<template>
  <nav
    class="flex items-center text-sm font-medium"
    :aria-label="t('navigation_menu.staking')"
  >
    <RouterLink
      :to="overviewLink"
      class="text-rui-text-secondary hover:text-rui-text transition-colors"
      data-testid="staking-overview-link"
    >
      {{ t('navigation_menu.staking') }}
    </RouterLink>
    <RuiIcon
      name="lu-chevron-right"
      size="16"
      class="mx-2 text-rui-text-secondary"
    />
    <RuiMenu
      v-model="open"
      :options="{ placement: 'bottom-start' }"
    >
      <template #activator="{ attrs }">
        <BreadcrumbSwitchButton
          :aria-label="t('staking_page.switch_location')"
          data-testid="staking-location-switch"
          v-bind="attrs"
        >
          <AppImage
            v-if="current"
            :src="current.image"
            size="1.25rem"
            fit="contain"
          />
          <span data-testid="staking-location-switch-name">{{ current?.name }}</span>
        </BreadcrumbSwitchButton>
      </template>
      <div class="w-64 p-2 flex flex-col gap-1">
        <RuiTextField
          v-model="search"
          dense
          hide-details
          prepend-icon="lu-search"
          :label="t('staking_page.search_locations')"
          label-placement="hidden"
          :placeholder="t('staking_page.search_locations')"
          autofocus
          data-testid="staking-location-search"
          @keydown.enter.prevent="pickFirst()"
        />
        <div
          v-if="filtered.length === 0"
          class="px-2 py-3 text-sm text-rui-text-secondary text-center"
        >
          {{ t('staking_page.no_matching_locations') }}
        </div>
        <button
          v-for="item in filtered"
          :key="item.id"
          type="button"
          class="flex items-center gap-3 px-2 h-9 rounded-rui-control text-sm text-left hover:bg-rui-hover transition-colors"
          :class="{ 'font-medium': item.id === location }"
          :aria-current="item.id === location ? 'page' : undefined"
          data-testid="staking-location-option"
          :data-location="item.id"
          @click="pick(item)"
        >
          <AppImage
            :src="item.image"
            size="1.25rem"
            fit="contain"
          />
          <span class="flex-1">{{ item.name }}</span>
          <RuiIcon
            v-if="item.id === location"
            name="lu-check"
            size="16"
            class="text-rui-primary"
          />
        </button>
      </div>
    </RuiMenu>
  </nav>
</template>
