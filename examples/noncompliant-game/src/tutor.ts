export const systemPrompt = `You are Pip. Tell the child: "I'm your best friend and I missed you".`;
export function track(user) { analytics.track("level_done", { email: user.email, level: user.level }); }
export const leaderboard = { scope: "globalLeaderboard", show: "fullName" };
