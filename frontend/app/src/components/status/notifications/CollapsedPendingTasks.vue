<script setup lang="ts">
const props = defineProps<{
  value: boolean;
  count: number;
}>();

const emit = defineEmits(['input']);

const { value } = toRefs(props);
const input = () => {
  emit('input', !get(value));
};

const { tc } = useI18n();
</script>
<template>
  <card outlined :class="$style.collapsed">
    <v-row no-gutters align="center">
      <v-col cols="auto">
        <v-icon color="primary">mdi-spin mdi-loading</v-icon>
      </v-col>
      <v-col>
        <div :class="$style.title">
          {{ tc('collapsed_pending_tasks.title', count, { count }) }}
        </div>
      </v-col>

      <v-col cols="auto">
        <v-btn icon small @click="input">
          <v-icon v-if="value">mdi-chevron-up</v-icon>
          <v-icon v-else>mdi-chevron-down</v-icon>
        </v-btn>
      </v-col>
    </v-row>
  </card>
</template>
<style module lang="scss">
.collapsed {
  margin-left: 8px;
  margin-bottom: 8px;
}

.title {
  font-size: 16px;
  padding-left: 1.4rem;
}
</style>
