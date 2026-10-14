<script setup lang="ts">
import type { StakingLocation } from '@/pages/staking/staking-pages';
import type { StakingInfo } from '@/pages/staking/use-staking-locations';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import AppImage from '@/modules/shell/components/AppImage.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useStakingPage } from '@/pages/staking/use-staking-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.staking'), icon: 'lu-layers', section: 1, order: 60, drawer: 'staking' },
    noteLocation: NoteLocation.STAKING,
  },
  props: true,
});

const { location: locationProp } = defineProps<{
  location: StakingLocation | '';
}>();

const { t } = useI18n({ useScope: 'global' });

const search = ref<string>('');

const { getRedirectLink, page, staking } = useStakingPage(() => locationProp);

/** Matched against the name and what the location tracks, so "validator" finds the ETH card. */
const filtered = computed<StakingInfo[]>(() => {
  const query = get(search).trim().toLocaleLowerCase();
  if (!query)
    return get(staking);
  return get(staking).filter(item => `${item.name} ${item.description}`.toLocaleLowerCase().includes(query));
});
</script>

<template>
  <div class="container">
    <div
      v-if="page"
      data-testid="staking-page"
    >
      <Component :is="page" />
    </div>
    <TablePageLayout
      v-else
      :title="[t('navigation_menu.staking')]"
      child
      data-testid="staking-picker"
    >
      <template #buttons>
        <div class="w-full sm:w-64">
          <RuiTextField
            v-model="search"
            dense
            hide-details
            clearable
            prepend-icon="lu-search"
            :label="t('staking_page.search_locations')"
            label-placement="hidden"
            :placeholder="t('staking_page.search_locations')"
            data-testid="staking-location-filter"
          />
        </div>
      </template>

      <div
        v-if="filtered.length > 0"
        class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      >
        <RouterLink
          v-for="item in filtered"
          :key="item.id"
          :to="getRedirectLink(item.id)"
          class="flex items-center gap-4 p-4 rounded-rui-card border border-rui-divider bg-rui-surface hover:border-rui-primary-border hover:bg-rui-primary-subtle transition-colors"
          data-testid="staking-location-card"
          :data-location="item.id"
        >
          <AppImage
            :src="item.image"
            size="2.5rem"
            fit="contain"
            class="shrink-0"
          />
          <div class="flex flex-col gap-0.5 min-w-0">
            <span class="text-base font-medium text-rui-text">{{ item.name }}</span>
            <span class="text-sm text-rui-text-secondary">{{ item.description }}</span>
          </div>
          <RuiIcon
            name="lu-chevron-right"
            size="16"
            class="ml-auto shrink-0 text-rui-text-secondary"
          />
        </RouterLink>
      </div>
      <div
        v-else
        class="py-16 text-center text-sm text-rui-text-secondary"
        data-testid="staking-location-none"
      >
        {{ t('staking_page.no_matching_locations') }}
      </div>
    </TablePageLayout>
  </div>
</template>
