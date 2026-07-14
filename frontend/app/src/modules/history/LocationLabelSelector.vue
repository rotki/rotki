<script setup lang="ts">
import type { LocationLabel } from '@/modules/core/common/location';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useLocationLabels } from '@/modules/history/use-location-labels';
import { useScramble } from '@/modules/settings/use-scramble';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

defineOptions({
  name: 'LocationLabelSelector',
  inheritAttrs: false,
});

const modelValue = defineModel<string[] | string>({
  required: true,
  set: (val: string[] | string | undefined) => val ?? '',
});

const { options } = defineProps<{
  options?: LocationLabel[];
}>();

const { t } = useI18n({ useScope: 'global' });
const { scrambleAddress } = useScramble();

const {
  filter,
  getAccountName,
  getBlockchainLocation,
  getTags,
  locationLabelOptions,
} = useLocationLabels(() => options);

const [DefineLocationItem, ReuseLocationItem] = createReusableTemplate<{ item: LocationLabel; dense: boolean }>();
</script>

<template>
  <DefineLocationItem #default="{ item, dense }">
    <div
      v-if="getBlockchainLocation(item.location)"
      class="flex items-center gap-2.5 min-w-0"
    >
      <EnsAvatar
        :address="scrambleAddress(item.locationLabel)"
        avatar
        class="shrink-0"
        :size="dense ? '22px' : '28px'"
      />
      <!-- field: keep the name and address on one compact line -->
      <div
        v-if="dense"
        class="flex items-baseline gap-1.5 min-w-0"
      >
        <span
          v-if="getAccountName(item)"
          class="truncate text-sm"
        >
          {{ getAccountName(item) }}
        </span>
        <span
          class="truncate font-mono text-xs"
          :class="getAccountName(item) ? 'text-rui-text-secondary' : 'text-rui-text'"
        >
          {{ truncateAddress(scrambleAddress(item.locationLabel), 4) }}
        </span>
      </div>
      <!-- dropdown: name over the muted address -->
      <div
        v-else
        class="flex flex-col min-w-0 leading-tight"
      >
        <span
          v-if="getAccountName(item)"
          class="truncate text-sm font-medium"
        >
          {{ getAccountName(item) }}
        </span>
        <span
          class="truncate font-mono text-xs"
          :class="getAccountName(item) ? 'text-rui-text-secondary' : 'text-rui-text'"
        >
          {{ truncateAddress(scrambleAddress(item.locationLabel), 10) }}
        </span>
      </div>
    </div>
    <div
      v-else
      class="flex items-center gap-2"
      :class="{ 'py-[5px]': !dense }"
    >
      <LocationIcon
        :item="item.location"
        class="overflow-hidden rounded-sm"
        :class="dense ? '!size-4' : '!size-6'"
        :size="dense ? '0.875rem' : '1.25rem'"
        icon
      />
      {{ item.locationLabel }}
    </div>
  </DefineLocationItem>
  <RuiAutoComplete
    v-model="modelValue"
    :options="locationLabelOptions"
    :item-height="56"
    clearable
    key-attr="locationLabel"
    text-attr="locationLabel"
    :filter="filter"
    :label="t('transactions.filter.account')"
    variant="outlined"
    menu-class="!min-w-full"
    v-bind="$attrs"
  >
    <template #selection="{ item }">
      <ReuseLocationItem
        :item="item"
        :dense="true"
      />
    </template>

    <template #item="{ item }">
      <ReuseLocationItem
        :item="item"
        :dense="false"
      />
      <TagDisplay
        class="pl-8 !mt-0"
        :tags="getTags(item)"
        small
      />
    </template>
  </RuiAutoComplete>
</template>
