<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import { SetAside } from '@/modules/shell/action-center/use-action-center-snooze';

interface SetAsideFilter {
  kind: SetAside;
  icon: RuiIcons;
  label: string;
  count: number;
}

/** the kinds of put-away rows listed in the set-aside group */
const revealed = defineModel<SetAside[]>('revealed', { default: () => [] });

const { counts } = defineProps<{
  /** how many raised rows were put away, by how */
  counts: Record<SetAside, number>;
}>();

const { t } = useI18n({ useScope: 'global' });

const filters = computed<SetAsideFilter[]>(() => {
  const all: SetAsideFilter[] = [
    { count: counts[SetAside.SNOOZED], icon: 'lu-alarm-clock', kind: SetAside.SNOOZED, label: t('action_center.set_aside.snoozed') },
    { count: counts[SetAside.MUTED], icon: 'lu-bell-off', kind: SetAside.MUTED, label: t('action_center.set_aside.muted') },
  ];
  return all.filter(filter => filter.count > 0);
});

function toggle(kind: SetAside): void {
  const others = get(revealed).filter(shown => shown !== kind);
  set(revealed, get(revealed).includes(kind) ? others : [...others, kind]);
}
</script>

<template>
  <div
    v-if="filters.length > 0"
    class="flex items-center gap-1"
    data-testid="actions-center-set-aside"
  >
    <button
      v-for="filter in filters"
      :key="filter.kind"
      type="button"
      class="flex items-center gap-1 rounded-full border px-2 py-0.5 text-caption transition-colors"
      :class="revealed.includes(filter.kind)
        ? 'border-rui-primary bg-rui-primary/10 text-rui-primary'
        : 'border-default text-rui-text-secondary hover:text-rui-text'"
      :aria-pressed="revealed.includes(filter.kind)"
      :title="t('action_center.set_aside.toggle_hint')"
      data-testid="actions-center-set-aside-toggle"
      :data-key="filter.kind"
      @click="toggle(filter.kind)"
    >
      <RuiIcon
        :name="filter.icon"
        size="12"
      />
      {{ filter.label }}
      <span class="font-medium">{{ filter.count }}</span>
    </button>
  </div>
</template>
