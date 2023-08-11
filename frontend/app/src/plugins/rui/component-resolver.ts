import { type ComponentResolver } from 'unplugin-vue-components';

export function RuiComponentResolver(): ComponentResolver {
  return {
    type: 'component',
    resolve: (name: string) => {
      const prefix = 'Rui';
      if (name.startsWith(prefix)) {
        return {
          name,
          from: '@rotki/ui-library-compat/components'
        };
      }
    }
  };
}
