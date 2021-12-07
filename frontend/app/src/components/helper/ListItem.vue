<template>
  <span v-bind="$attrs" :class="$style.wrapper" @click="click">
    <slot name="icon" :class="$style.icon" />
    <span :class="$style.details">
      <span :class="$style.title" data-cy="details-symbol">
        {{ title }}
      </span>
      <span v-if="subtitle" class="grey--text" :class="$style.subtitle">
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

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { setupThemeCheck } from '@/composables/common';

export default defineComponent({
  name: 'ListItem',
  props: {
    title: {
      required: true,
      type: String
    },
    subtitle: {
      required: false,
      type: String as PropType<string | null>,
      default: null
    }
  },
  setup(props, { emit }) {
    const { subtitle } = toRefs(props);
    const { currentBreakpoint } = setupThemeCheck();
    const large = computed(() => currentBreakpoint.value.lgAndUp);
    const visibleSubtitle = computed(() => {
      const sub = subtitle.value;
      if (!sub) {
        return '';
      }
      const truncLength = 7;
      const small = currentBreakpoint.value.mdAndDown;
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

    return {
      visibleSubtitle,
      large,
      click
    };
  }
});
</script>

<style module lang="scss">
.wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
  margin-top: 12px;
  margin-bottom: 12px;

  @media (min-width: 700px) and (max-width: 1500px) {
    width: 100px;
  }
}

.icon {
  margin-right: 8px;
}

.details {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-left: 16px;

  @media (min-width: 700px) and (max-width: 1500px) {
    width: 100px;
  }
}

.title {
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;

  @media (min-width: 700px) and (max-width: 1500px) {
    width: 100px;
  }
}

.subtitle {
  font-size: 0.8rem;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;

  @media (min-width: 700px) and (max-width: 1500px) {
    width: 100px;
  }
}
</style>
