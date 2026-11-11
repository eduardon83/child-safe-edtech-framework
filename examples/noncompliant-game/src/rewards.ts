export function onAnswer(player, correct) {
  player.coins += 10;            // paid for every answer, right or wrong
  player.badges.push("daily-visitor");
  player.streak += 1;
  if (player.xp > 100) levelUp(player);
  updateLeaderboard(player);
  showConfetti();
}
