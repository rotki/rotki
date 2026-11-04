<script setup lang="ts">
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { locationAliasParams, toLocationAliasFields } from '@/modules/locations/location-manager-fields';

const alias = defineModel<string>('alias', { required: true });
const location = defineModel<string>('location', { required: true });

const { locations } = defineProps<{
  /** The locations the saved aliases point at. */
  locations: readonly string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const fields = toLocationAliasFields(useSharedFieldResolvers(), t, { locations: (): string[] => [...locations] });
const pillLabels = usePillBarLabels();
const params = locationAliasParams(alias, location);
</script>

<template>
  <PillFilterBar
    v-model:params="params"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
