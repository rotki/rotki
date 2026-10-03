import { BinaryComponent, BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';

/** colibri taken by antivirus on a Linux install, the report most specs need. */
export const QUARANTINED_COLIBRI: UnusableBinary = {
  component: BinaryComponent.COLIBRI,
  onWindows: false,
  path: '/opt/rotki/resources/colibri/colibri',
  status: BinaryStatus.MISSING,
};

export const QUARANTINED_STARLING: UnusableBinary = {
  component: BinaryComponent.STARLING,
  onWindows: false,
  path: '/opt/rotki/resources/starling/starling',
  status: BinaryStatus.MISSING,
};
