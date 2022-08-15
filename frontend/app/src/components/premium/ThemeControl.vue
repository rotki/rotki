<template>
  <div>
    <theme-switch
      v-if="premium && componentsLoaded"
      :dark-mode-enabled="darkModeEnabled"
      :class="{ [$style.menu]: menu }"
    />
    <theme-switch-lock v-else />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import ThemeSwitchLock from '@/components/premium/ThemeSwitchLock.vue';
import { ThemeSwitch } from '@/premium/premium';
import { usePremiumStore } from '@/store/session/premium';

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
    const { premium, componentsLoaded } = storeToRefs(usePremiumStore());

    return {
      premium,
      componentsLoaded
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
