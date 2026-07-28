<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import ShowInEventsButton from '@/modules/history/events/ShowInEventsButton.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import SimpleTable from '@/modules/shell/components/SimpleTable.vue';

defineProps<{
  entry: HistoryEventEntry;
  typeLabel: string;
  locationHeader: string;
}>();

const emit = defineEmits<{
  'show-in-events': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <!-- the row being matched, as a summary table; `PotentialMatchSubjectCard` is the pinned-width half -->
  <SimpleTable data-testid="potential-match-subject">
    <thead>
      <tr>
        <th>{{ t('common.datetime') }}</th>
        <th>{{ t('common.type') }}</th>
        <th class="!text-center">
          {{ locationHeader }}
        </th>
        <th>{{ t('common.asset') }}</th>
        <th />
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>
          <DateDisplay
            :timestamp="entry.timestamp"
            milliseconds
          />
        </td>
        <td>
          <BadgeDisplay>
            {{ typeLabel }}
          </BadgeDisplay>
        </td>
        <td class="text-center">
          <LocationDisplay
            horizontal
            :identifier="entry.location"
          />
        </td>
        <td>
          <HistoryEventAsset
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
