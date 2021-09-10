<template>
  <card>
    <v-row>
      <v-col cols="12">
        <div :class="$style.image">
          <slot name="image">
            <v-img max-width="200" :src="icon" />
          </slot>
        </div>
      </v-col>
    </v-row>
    <v-row v-if="singleSource">
      <v-col>
        <slot name="upload-title" />
        <file-upload :source="source" />
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col v-for="(src, index) in source" :key="src">
        <slot :name="`upload-title-${index}`" />
        <file-upload :source="src" />
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <slot />
      </v-col>
    </v-row>
    <v-row v-if="$slots.hint">
      <v-col cols="12">
        <slot name="hint" />
      </v-col>
    </v-row>
  </card>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import FileUpload from '@/components/import/FileUpload.vue';

export default defineComponent({
  name: 'ImportSource',
  components: { FileUpload },
  props: {
    icon: {
      required: false,
      default: '',
      type: String
    },
    source: { required: true, type: [String, Array] }
  },
  setup(props) {
    const { source } = toRefs(props);
    const singleSource = computed(() => typeof source.value === 'string');
    return {
      singleSource
    };
  }
});
</script>

<style module lang="scss">
.image {
  padding: 10px;
  max-width: 200px;
}
</style>
