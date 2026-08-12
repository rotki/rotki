<script lang="ts" setup>
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { useOracleCacheFields } from '@/modules/assets/prices/use-oracle-cache-fields';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';

const matches = defineModel<MatchedKeywordWithBehaviour<string>>('matches', { required: true });

const { disabled = false } = defineProps<{ disabled?: boolean }>();

const fields = useOracleCacheFields();
const pillLabels = usePillBarLabels();
</script>

<template>
  <PillFilterBar
    v-model:matches="matches"
    :disabled="disabled"
    :fields="fields"
    :labels="pillLabels"
  />
</template>
