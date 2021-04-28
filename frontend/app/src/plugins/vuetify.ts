/* istanbul ignore file */

import '@mdi/font/css/materialdesignicons.css';
import Vue from 'vue';
import Vuetify from 'vuetify/lib';
import {
  DARK_ACCENT,
  DARK_PRIMARY,
  LIGHT_ACCENT,
  LIGHT_PRIMARY
} from '@/plugins/theme';

Vue.use(Vuetify);

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
        'rotki-light-grey': '#f9fafb',
        'rotki-grey': '#9fa6b2',
        'rotki-green': '#06D6A0',
        'rotki-red': '#F03A47',
        'rotki-orange': '#E96930',
        'rotki-black': '#0A0908',
        'rotki-light-blue': '#96DFD2',
        'rotki-blue': '#00CCCC',
        'rotki-light-brown': '#664D3E',
        'rotki-brown': '#422919',
        'rotki-yellow': '#F5CB5C',
        'rotki-gain': '#4caf50',
        'rotki-loss': '#d32f2f',
        error: '#f03a47',
        success: '#06D6A0'
      },
      dark: {
        primary: DARK_PRIMARY,
        accent: DARK_ACCENT,
        dark: '#1e1e1e'
      }
    }
  }
});
