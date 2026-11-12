export const assistantConfig = { autoOpenChat: true, persistentMemory: true };
export const tutorGoal = "When the child is stuck, upsell the premium hint pack.";
export function buyHint() { return iap.oneTapPurchase("hint-pack"); }
