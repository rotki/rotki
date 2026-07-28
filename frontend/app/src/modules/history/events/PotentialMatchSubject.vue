<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import PotentialMatchSubjectCard from '@/modules/history/events/PotentialMatchSubjectCard.vue';
import ShowInEventsButton from '@/modules/history/events/ShowInEventsButton.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import SimpleTable from '@/modules/shell/components/SimpleTable.vue';

defineProps<{
  entry: HistoryEventEntry;
  typeLabel: string;
  locationHeader: string;
  isPinned?: boolean;
}>();

const emit = defineEmits<{
  'show-in-events': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <PotentialMatchSubjectCard
    v-if="isPinned"
    :entry="entry"
    :type-label="typeLabel"
    @show-in-events="emit('show-in-events')"
  />

  <SimpleTable v-else>
    <thead>
      <tr>
        <th>{{ t('common.datetime') }}</th>
        <th>{{ t('common.type') }}</th>
        <th
          v-if="!isPinned"
          class="!text-center"
        >
          {{ locationHeader }}
        </th>
        <th>{{ t('common.asset') }}</th>
        <th />
      </tr>
    </thead>
    <tbody>
      <tr :class="{ 'bg-rui-warning/15': isPinned }">
        <td>
          <DateDisplay
            :timestamp="entry.timestamp"
            milliseconds
          />
        </td>
        <td>
          <BadgeDisplay :class="{ '!leading-6 mb-1': isPinned }">
            {{ typeLabel }}
          </BadgeDisplay>
          <LocationDisplay
            v-if="isPinned"
            class="[&_div]:!justify-start"
            size="16px"
            :identifier="entry.location"
            horizontal
          />
        </td>
        <td
          v-if="!isPinned"
          class="text-center"
        >
          <LocationDisplay
            horizontal
            :identifier="entry.location"
          />
        </td>
        <td>
          <HistoryEventAsset
            :dense="isPinned"
            disable-options
            :event="entry"
          />
        </td>
        <td class="text-right">
          <ShowInEventsButton @click="emit('show-in-events')" />
        </td>
      </tr>
    </tbody>
  </SimpleTable>
</template>
