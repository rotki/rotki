<template>
  <span
    v-bind="rootAttrs"
    :class="{
      [css.wrapper]: true,
      [css.dense]: dense
    }"
    @click="click"
  >
    <slot name="icon" :class="css.icon" />
    <span v-if="showDetails" :class="css.details">
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
    </span>
  </span>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';

const props = defineProps({
  title: {
    required: false,
    type: String,
    default: ''
  },
  subtitle: {
    required: false,
    type: String as PropType<string | null>,
    default: null
  },
  dense: { required: false, type: Boolean, default: false },
  showDetails: {
    required: false,
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['click']);
const { subtitle } = toRefs(props);
const { currentBreakpoint } = useTheme();
const css = useCssModule();
const rootAttrs = useAttrs();
const large = computed(() => get(currentBreakpoint).lgAndUp);
const visibleSubtitle = computed(() => {
  const sub = get(subtitle);
  if (!sub) {
    return '';
  }
  const truncLength = 7;
  const small = get(currentBreakpoint).mdAndDown;
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

<style module lang="scss">
.wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;

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

  @media (min-width: 700px) and (max-width: 1200px) {
    width: 100px;
  }
}

.title {
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  font-weight: 500;

  @media (min-width: 700px) and (max-width: 1200px) {
    width: 100px;
  }
}

.subtitle {
  font-size: 0.8rem;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;

  @media (min-width: 700px) and (max-width: 1200px) {
    width: 100px;
  }
}
</style>
