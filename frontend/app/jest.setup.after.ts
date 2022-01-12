import "@testing-library/jest-dom/extend-expect";
import "@testing-library/jest-dom";
import VueCompositionAPI from "@vue/composition-api";
import Vue from "vue";
import { PiniaVuePlugin } from "pinia";

Vue.config.productionTip = false;
Vue.config.devtools = false;
Vue.use(VueCompositionAPI);
Vue.use(PiniaVuePlugin);
