<template>
  <div>
    <theme-switch
      v-if="premium"
      :dark-mode-enabled="darkModeEnabled"
      :class="{ [$style.menu]: menu }"
    />
    <theme-switch-lock v-else />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ThemeSwitchLock from '@/components/premium/ThemeSwitchLock.vue';
import { getPremium } from '@/composables/session';
import { ThemeSwitch } from '@/premium/premium';

export default defineComponent({
  name: 'ThemeControl',
  components: {
    ThemeSwitch,
    ThemeSwitchLock
  },
  props: {
    darkModeEnabled: {
      required: true,
      type: Boolean
    },
    menu: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  setup() {
    const premium = getPremium();

    return {
      premium
    };
  }
});
</script>

<style lang="scss" module>
.menu {
  :global {
    .v-icon {
      color: var(--v-primary-base) !important;
      caret-color: var(--v-primary-base) !important;
    }
  }
}
</style>
