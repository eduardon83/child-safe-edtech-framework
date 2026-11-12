import { io } from "socket.io-client";
const socket = io("https://chat.example.org");
export function sendChatMessage(text: string) { socket.emit("message", text); }
export function directMessage(userId: string, text: string) { socket.emit("dm", { userId, text }); }
export function randomMatch() { socket.emit("match:random"); }
export const voiceSettings = { voiceChatEnabled: true };
export function sendImage(file: Blob) { socket.emit("image", file); }
