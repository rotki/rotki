<script setup lang="ts">
import type { Filters } from '@/modules/assets/detection/use-newly-detected-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';

const filtersModel = defineModel<Filters>('filters', { required: true });

const {
  allSelected,
  selectedCount,
  found,
  fields,
} = defineProps<{
  allSelected: boolean;
  selectedCount: number;
  found: number;
  fields: FieldDef[];
}>();

const emit = defineEmits<{
  'toggle-selection': [];
  'accept': [];
  'mark-spam': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();
</script>

<template>
  <div class="flex flex-col gap-4 px-4 pt-4">
    <div class="flex gap-4 justify-between grow">
      <div class="flex gap-4 content-center">
        <RuiTooltip
          :popper="{ placement: 'bottom' }"
          :open-delay="500"
        >
          <template #activator>
            <RuiCheckbox
              color="primary"
              hide-details
              size="sm"
              class="ml-2 mt-1 text-body-2"
              :disabled="found === 0"
              :model-value="allSelected"
              @update:model-value="emit('toggle-selection')"
            >
              {{ t('asset_table.selected', { count: selectedCount }) }}
            </RuiCheckbox>
          </template>
          {{ t('asset_table.newly_detected.select_deselect_all_tokens') }}
        </RuiTooltip>

        <div>
          <RuiTooltip
            :popper="{ placement: 'bottom' }"
            :open-delay="500"
          >
            <template #activator>
              <RuiButton
                :disabled="selectedCount === 0"
                color="success"
                variant="text"
                class="w-12 h-12"
                data-testid="accept-selected"
                @click="emit('accept')"
              >
                <RuiIcon name="lu-check" />
              </RuiButton>
            </template>

            {{ t('asset_table.newly_detected.accept_selected') }}
          </RuiTooltip>

          <RuiTooltip
            :popper="{ placement: 'bottom' }"
            :open-delay="500"
          >
            <template #activator>
              <RuiButton
                :disabled="selectedCount === 0"
                color="error"
                variant="text"
                class="w-12 h-12"
                data-testid="mark-selected-spam"
                @click="emit('mark-spam')"
              >
                <RuiIcon name="lu-octagon-alert" />
              </RuiButton>
            </template>

            {{ t('asset_table.newly_detected.mark_selected_as_spam') }}
          </RuiTooltip>
        </div>
      </div>

      <HintMenuIcon :popper="{ placement: 'left-start' }">
        {{ t('asset_table.newly_detected.subtitle') }}
      </HintMenuIcon>
    </div>

    <!-- Filters. Absent when there is nothing to narrow by, which is every user tracking no
         solana account: the field list is empty and the bar draws nothing. -->
    <div
      v-if="fields.length > 0"
      class="flex gap-4 items-center"
    >
      <PillFilterBar
        v-model:matches="filtersModel"
        class="flex-1 min-w-[12rem] md:min-w-[24rem]"
        :fields="fields"
        :labels="pillLabels"
      />
    </div>
  </div>
</template>
