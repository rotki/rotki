/* istanbul ignore file */

import '@mdi/font/css/materialdesignicons.css';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { VSwitch } from 'vuetify/lib/components';
import {
  DARK_ACCENT,
  DARK_GRAPH,
  DARK_PRIMARY,
  LIGHT_ACCENT,
  LIGHT_GRAPH,
  LIGHT_PRIMARY
} from '@/plugins/theme';

Vue.use(Vuetify);
// @ts-ignore
VSwitch.options.props.inset.default = true;

const DARK_GREY = '#1e1e1e';

export default new Vuetify({
  icons: {
    iconfont: 'mdi'
  },
  theme: {
    options: {
      customProperties: true
    },
    themes: {
      light: {
        primary: LIGHT_PRIMARY,
        secondary: '#0a0908',
        accent: LIGHT_ACCENT,
        graph: LIGHT_GRAPH,
        graphFade: '#ffffff',
        error: '#f03a47',
        success: '#06D6A0',
        'rotki-light-grey': '#f9fafb',
        'rotki-grey': '#9fa6b2',
        'rotki-green': '#06D6A0',
        'rotki-red': '#F03A47',
        'rotki-gain': '#4caf50',
        'rotki-loss': '#d32f2f',
        'rotki-scrollbar': '#eeeeee'
      },
      dark: {
        primary: DARK_PRIMARY,
        accent: DARK_ACCENT,
        graph: DARK_GRAPH,
        graphFade: DARK_GREY,
        dark: DARK_GREY,
        'rotki-light-grey': '#121212',
        'rotki-green': '#4caf50',
        'rotki-red': '#d32f2f',
        'rotki-scrollbar': '#999999'
      }
    }
  }
});
