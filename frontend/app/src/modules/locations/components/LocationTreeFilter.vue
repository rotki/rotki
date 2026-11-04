<script setup lang="ts">
import { stringParam, toPillParams } from '@/modules/core/table/param-refs';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { toLocationTreeFields } from '@/modules/locations/location-manager-fields';

const name = defineModel<string>('name', { required: true });

const { t } = useI18n({ useScope: 'global' });

const fields = toLocationTreeFields(t);
const pillLabels = usePillBarLabels();
const params = toPillParams({ locationName: stringParam(name) });
</script>

<template>
  <PillFilterBar
    v-model:params="params"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
