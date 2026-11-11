export function openLootBox(player: Player) {
  const reward = randomReward(player.level);
  return reward;
}
export const offerBanner = "Only 3 left! Offer ends in 10 minutes";
export function buyGems(pack: number) { return iap.purchase("gemPack" + pack); }
