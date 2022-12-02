import { BigNumber } from '@rotki/common';
import { checkIfDevelopment } from '@/utils/env-utils';

export function setupFormatter(): void {
  if (!checkIfDevelopment()) {
    return;
  }
  // @ts-ignore
  window.devtoolsFormatters = [
    {
      header: (obj: any): {}[] | null => {
        if (!(obj instanceof BigNumber)) {
          return null;
        }
        return ['div', {}, obj.toString()];
      },
      hasBody: (): boolean => false
    }
  ];
}
