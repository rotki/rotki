import { BinaryComponent, BinaryPlatform, BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';

/** colibri taken by antivirus on a Linux install, the report most specs need. */
export const QUARANTINED_COLIBRI: UnusableBinary = {
  component: BinaryComponent.COLIBRI,
  path: '/opt/rotki/resources/colibri/colibri',
  platform: BinaryPlatform.LINUX,
  status: BinaryStatus.MISSING,
};

export const QUARANTINED_STARLING: UnusableBinary = {
  component: BinaryComponent.STARLING,
  path: '/opt/rotki/resources/starling/starling',
  platform: BinaryPlatform.LINUX,
  status: BinaryStatus.MISSING,
};
