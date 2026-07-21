<script setup lang="ts">
import type { NewDetectedTokenKind } from './types';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';

interface TokenKindOption {
  title: string;
  value: NewDetectedTokenKind | undefined;
}

const tokenKindFilter = defineModel<NewDetectedTokenKind>();

const {
  allSelected,
  selectedCount,
  found,
  tokenKindOptions,
} = defineProps<{
  allSelected: boolean;
  selectedCount: number;
  found: number;
  tokenKindOptions: TokenKindOption[];
}>();

const emit = defineEmits<{
  'toggle-selection': [];
  'accept': [];
  'mark-spam': [];
}>();

const { t } = useI18n({ useScope: 'global' });
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

    <!-- Filters -->
    <div class="flex gap-4 items-center">
      <RuiMenuSelect
        v-model="tokenKindFilter"
        :options="tokenKindOptions"
        :label="t('asset_table.newly_detected.token_type')"
        key-attr="value"
        text-attr="title"
        variant="outlined"
        dense
        hide-details
        class="max-w-[180px]"
      />
    </div>
  </div>
</template>
