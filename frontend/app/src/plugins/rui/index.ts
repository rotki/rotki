import type { App } from 'vue';
import {
  createRui,
  type RuiOptions,
  ThemeMode,
} from '@rotki/ui-library';
import detectedIcons from 'virtual:rotki-icons';
import '@rotki/ui-library/style.css';

interface RuiPlugin {
  install: (app: App) => void;
}

export function createRuiPlugin(defaults: Partial<RuiOptions['defaults']>): RuiPlugin {
  return createRui({
    defaults,
    theme: {
      icons: detectedIcons,
      mode: ThemeMode.light,
    },
  });
}
