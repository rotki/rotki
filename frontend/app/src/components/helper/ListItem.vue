<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    title?: string;
    subtitle?: string | null;
    dense?: boolean;
    showDetails?: boolean;
    loading?: boolean;
    fullWidth?: boolean;
  }>(),
  {
    title: '',
    subtitle: null,
    dense: false,
    showDetails: true,
    loading: false,
    fullWidth: true
  }
);

const emit = defineEmits(['click']);
const { subtitle } = toRefs(props);
const css = useCssModule();
const rootAttrs = useAttrs();
const { lgAndUp: large, mdAndDown } = useDisplay();

const visibleSubtitle = computed(() => {
  const sub = get(subtitle);
  if (!sub) {
    return '';
  }
  const truncLength = 7;
  const small = get(mdAndDown);
  const length = sub.length;

  if (!small || (length <= truncLength * 2 && small)) {
    return sub;
  }

  return `${sub.slice(0, truncLength)}...${sub.slice(
    length - truncLength,
    length
  )}`;
});

const click = () => emit('click');
</script>

<template>
  <span
    v-bind="rootAttrs"
    :class="{
      [css.wrapper]: true,
      [css.dense]: dense,
      [css['full-width']]: fullWidth
    }"
    @click="click()"
  >
    <slot name="icon" :class="css.icon" />
    <span v-if="showDetails" :class="css.details">
      <template v-if="loading">
        <v-skeleton-loader width="30" height="21" type="text" class="pt-1" />
        <v-skeleton-loader width="70" type="text" height="18" />
      </template>

      <template v-else>
        <span :class="css.title" data-cy="details-symbol">
          {{ title }}
        </span>
        <span v-if="subtitle" class="grey--text" :class="css.subtitle">
          <v-tooltip open-delay="400" top :disabled="large">
            <template #activator="{ on, attrs }">
              <span v-bind="attrs" class="text-truncate" v-on="on">
                {{ visibleSubtitle }}
              </span>
            </template>
            <span> {{ subtitle }}</span>
          </v-tooltip>
        </span>
      </template>
    </span>
  </span>
</template>

<style module lang="scss">
.wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;

  &.full-width {
    width: 100%;
  }

  &:not(.dense) {
    margin-top: 12px;
    margin-bottom: 12px;
  }

  &.dense {
    margin-top: 4px;
    margin-bottom: 4px;
  }
}

.icon {
  margin-right: 8px;
}

.details {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 200px;
  margin-left: 1rem;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.title {
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  font-weight: 500;
}

.subtitle {
  font-size: 0.75rem;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}
</style>
