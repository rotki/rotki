import { BigNumber } from '@rotki/common';

export function setupFormatter(): void {
  if (!checkIfDevelopment()) {
    return;
  }
  // @ts-ignore
  window.devtoolsFormatters = [
    {
      header: (obj: any): unknown[] | null => {
        if (!(obj instanceof BigNumber)) {
          return null;
        }
        return ['div', {}, obj.toString()];
      },
      hasBody: (): boolean => false
    }
  ];
}
