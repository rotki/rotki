<script setup lang="ts">
import { type IssueKind, KIND_META } from '@/modules/history/data-issues/constants';
import { useDataIssuesFormat } from '@/modules/history/data-issues/use-data-issues-format';

const { kind } = defineProps<{
  kind: IssueKind;
}>();

const { kindLabel } = useDataIssuesFormat();

const meta = computed(() => KIND_META[kind]);
</script>

<template>
  <RuiChip
    size="sm"
    variant="outlined"
    :color="meta.color"
    data-testid="data-issue-kind-chip"
  >
    <div class="flex items-center gap-1.5">
      <RuiIcon
        :name="meta.icon"
        size="14"
      />
      <span>{{ kindLabel(kind) }}</span>
    </div>
  </RuiChip>
</template>
