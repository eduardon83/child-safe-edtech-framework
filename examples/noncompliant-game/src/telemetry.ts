// Fictional example of what NOT to do (CSEF CORE-DAT-19 to 24).
import { createHash } from "crypto";
import analytics from "./analytics";

// Player code derived from the email: reversible by guessing (CORE-DAT-20).
export const playerCode = (user: { email: string }) => createHash("sha256").update(user.email).digest("hex");

export function levelDone(user: { email: string }, level: number) {
  // Device details in every event: fingerprinting (CORE-DAT-21).
  analytics.track("level_done", { player: playerCode(user), level, ua: navigator.userAgent, w: screen.width });
  logEvent("bonus_chest_opened", { level });           // not in any event catalogue (CORE-DAT-19)
}

// Growth targets for children (CORE-DAT-23).
export const OKR = { d7_retention: 0.45, session_length_target: 35 };

declare function logEvent(name: string, data: object): void;
