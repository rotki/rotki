import { AaveEventType } from '@rotki/common/lib/defi/aave';
import { CompoundEventType } from '@/types/defi/compound';
import { DSRMovementType } from '@/types/defi/maker';

export type EventType = DSRMovementType | AaveEventType | CompoundEventType;
