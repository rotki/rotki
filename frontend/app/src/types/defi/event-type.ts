import { type AaveEventType } from '@rotki/common/lib/defi/aave';
import { type CompoundEventType } from '@/types/defi/compound';
import { type DSRMovementType } from '@/types/defi/maker';

export type EventType = DSRMovementType | AaveEventType | CompoundEventType;
