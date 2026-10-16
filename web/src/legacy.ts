// A08 validation and cast timing stay the single source of truth during migration.
// @ts-expect-error Legacy global script intentionally has no TypeScript declarations.
import '../../game/survival-rules.js';
// @ts-expect-error Legacy global script intentionally has no TypeScript declarations.
import '../../game/cast-motion.js';
import type { RaftRules, CastMotion } from './types';
export const rules:RaftRules = window.RaftRules;
export const castMotion:CastMotion = window.RaftCastMotion;
