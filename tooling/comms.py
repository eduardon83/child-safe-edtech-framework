"""CSES communications inventory.

Finds communication channels in a codebase (text chat, direct messages, voice and video, comments,
live streaming) and the safeguards around them (reporting, blocking, moderation roles, automated
filters, link filtering, rate limiting, preset messages, retention).

Absence of a safeguard in code is a signal, not proof: it may live in a third-party dashboard or a
backend outside the repository. Findings built on this inventory are therefore REVIEW, not BLOCK,
unless a risky default is explicit in code.

Licence: Apache-2.0
"""
from __future__ import annotations

import re

CODE_EXT = (".prefab", ".asset", ".unity", ".tscn", ".tres", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".html", ".py", ".java", ".kt", ".swift",
            ".dart", ".cs", ".go", ".rb", ".php", ".gd", ".lua", ".sql", ".rules", ".json", ".yaml", ".yml")

CHANNELS = [
    # name, kind, dependency names, code regex
    ("Stream Chat", "text chat", ["stream-chat", "stream-chat-react", "stream-chat-react-native", "stream_chat_flutter", "stream-chat-android"], None),
    ("Sendbird", "text chat", ["@sendbird/chat", "sendbird", "@sendbird/uikit-react", "sendbird_chat_sdk"], None),
    ("PubNub", "text chat", ["pubnub", "pubnub-react", "pubnub_flutter"], None),
    ("Twilio Conversations", "text chat", ["@twilio/conversations", "twilio-chat"], None),
    ("CometChat", "text chat", ["@cometchat/chat-sdk-javascript", "@cometchat-pro/chat", "@cometchat/chat-uikit-react"], None),
    ("TalkJS", "text chat", ["talkjs", "@talkjs/react"], None),
    ("Ably", "realtime messaging", ["ably", "@ably/chat"], None),
    ("Pusher", "realtime messaging", ["pusher-js", "pusher"], None),
    ("Matrix", "text chat", ["matrix-js-sdk"], None),
    ("Socket.IO", "realtime messaging", ["socket.io", "socket.io-client", "flask-socketio", "python-socketio"], None),
    ("Discord SDK", "text and voice", ["@discord/embedded-app-sdk", "discord.js", "discord-game-sdk"], None),
    ("Photon Chat", "text chat", [], r"\bPhoton\.Chat\b|\bChatClient\s*\("),
    ("Firebase / Firestore messages", "text chat", [], r"collection\(\s*['\"](messages|chats|chat_messages|conversations)['\"]"),
    ("Supabase realtime messages", "text chat", [], r"\.channel\([^)]*\)[\s\S]{0,200}?(messages|chat)|from\(\s*['\"](messages|chat_messages|conversations)['\"]\s*\)"),
    ("Database message tables", "text chat", [], r"create\s+table\s+(if\s+not\s+exists\s+)?[\w.\"]*(messages|chat_messages|direct_messages|conversations)\b"),
    ("Chat code", "text chat", [], r"\b(sendChatMessage|send_chat_message|chatMessages?|chat_messages|ChatInput|ChatWindow|MessageList|createMessage)\b"),
    ("Agora", "voice / video", ["agora-rtc-sdk-ng", "agora-rtc-react", "react-native-agora", "agora_rtc_engine"], None),
    ("Twilio Video", "voice / video", ["twilio-video", "@twilio/video-react-sdk"], None),
    ("LiveKit", "voice / video", ["livekit-client", "@livekit/components-react", "livekit_client"], None),
    ("Daily", "voice / video", ["@daily-co/daily-js", "@daily-co/daily-react"], None),
    ("Zoom Video SDK", "voice / video", ["@zoom/videosdk"], None),
    ("Jitsi", "voice / video", ["lib-jitsi-meet", "@jitsi/react-sdk"], None),
    ("100ms", "voice / video", ["@100mslive/react-sdk", "@100mslive/hms-video-store"], None),
    ("PeerJS / WebRTC", "voice / video", ["peerjs", "simple-peer"], r"\bnew\s+RTCPeerConnection\b"),
    ("Vivox / Photon Voice", "voice / video", ["com.unity.services.vivox"], r"\bVivox(Unity)?\b|\bPhoton\.Voice\b|\bVivoxService\b"),
    ("Unity multiplayer text chat", "text chat", [], r"\b(SendChatMessage|ChatMessageRpc|OnChatMessage)\b"),
    ("Photon PUN / Fusion rooms", "multiplayer", [], r"\bPhoton\.(Pun|Realtime|Fusion)\b"),
    ("Comments", "comments", [], r"\b(addComment|postComment|commentsEnabled|comment_thread|CommentBox)\b"),
    ("Live streaming", "live streaming", [], r"\b(startLiveStream|goLive|startBroadcast|createLivestream|startStreaming)\b"),
]

SAFEGUARDS = {
    "report": ("Report button or function", r"\b(report(Message|User|Content|Abuse|Player|Post)|flag(Message|Content|User|Post)|abuseReport|reportButton|onReport|denunciar)\b", []),
    "block": ("Block or mute", r"\b(block(User|Contact|Player|ed_?users)|mute(User|Player)|ignoreUser|unblock(User|Player)|bloquear)\b", []),
    "moderation_role": ("Moderator or teacher role with powers", r"\b(isModerator|moderators?|modRole|canModerate|moderationQueue|ban(User|Player)|kick(User|Player)|timeout(User|Player)|hideMessage|removeMessage)\b|role\s*(===?|==|:|=)\s*['\"](moderator|mod|teacher)['\"]", []),
    "auto_filter": ("Automated text or image filter", r"\b(profanityFilter|filterProfanity|isProfane|containsProfanity|moderateText|moderateImage|moderations\.create|contentSafety|wordFilter|censor\(|toxicity|DetectToxicContent|commentanalyzer\.googleapis)\b",
                    ["bad-words", "leo-profanity", "obscenity", "@2toad/profanity", "profanity-check", "better-profanity", "naughty-words",
                     "@azure-rest/ai-content-safety", "@azure/ai-content-safety", "glin-profanity", "nsfwjs"]),
    "link_filter": ("Link and contact-detail filtering", r"\b(stripLinks|removeUrls|blockLinks|linkFilter|noLinks|containsUrl|stripUrls|disallowLinks|maskPhone|redactPII|removeContactDetails|filterContactInfo)\b", []),
    "rate_limit": ("Rate limiting or slow mode", r"\b(rateLimit|rate_limit|throttleMessages|slowMode|messageCooldown|antiSpam)\b", ["express-rate-limit", "rate-limiter-flexible", "@upstash/ratelimit"]),
    "preset_messages": ("Preset messages (quick chat)", r"\b(quickChat|presetMessages|cannedMessages|predefinedPhrases|safeChat|emojiOnly|phrasePicker)\b", []),
    "retention": ("Message deletion or retention", r"\b(deleteMessage|messageRetention|retentionDays|expireMessages|purgeMessages|message_ttl)\b", []),
    "teacher_visibility": ("Teacher or guardian visibility of conversations", r"\b(teacherView|teacherCanSee|guardianView|classChatLog|supervisedChat|monitorChat)\b", []),
}

RISKS = {
    "direct_messages": ("Direct or private messages", r"\b(directMessages?|direct_messages|privateMessage|createDM|openDM|whisper|privateChat|sendDirect)\b"),
    "open_discovery": ("Contact with unknown users (random matching, public rooms, user search)", r"\b(randomMatch|matchmakeRandom|findRandomPlayer|publicLobby|joinPublicRoom|globalChat|worldChat|openLobby|searchUsers|findFriends|friendSuggestions|peopleYouMayKnow)\b"),
    "voice_default_on": ("Voice or video on by default", r"\b(voiceChatEnabled|enableVoiceChat|micEnabled|autoJoinVoice|videoEnabled|cameraEnabled)\s*[:=]\s*(true|1)\b"),
    "media_sharing": ("Images or files shared in messages", r"\b(sendImage|sendPhoto|uploadAttachment|sendAttachment|imageMessage|sendFile)\b"),
    "livestream": ("Children can host live streams", r"\b(startLiveStream|goLive|startBroadcast|createLivestream)\b"),
}


def _first_hits(rx, files_cache, limit=5):
    c = re.compile(rx, re.I | re.M)
    hits = []
    for rel, lines, text in files_cache:
        if not rel.endswith(CODE_EXT) or not c.search(text):
            continue
        for i, ln in enumerate(lines):
            if c.search(ln):
                hits.append(f"{rel}:{i + 1}")
                break
        if len(hits) >= limit:
            break
    if not hits:
        # multi-line patterns (e.g. Supabase channel ... messages)
        for rel, lines, text in files_cache:
            if rel.endswith(CODE_EXT) and c.search(text):
                hits.append(rel)
                if len(hits) >= limit:
                    break
    return hits


def _dep_hits(names, deps):
    lower = {k.lower(): (k, v) for k, v in deps.items()}
    return [f"{lower[n.lower()][1]} (dependency: {lower[n.lower()][0]})" for n in names if n.lower() in lower]


def inventory(files_cache, deps) -> dict:
    channels = []
    for name, kind, dep_names, rx in CHANNELS:
        ev = _dep_hits(dep_names, deps) + (_first_hits(rx, files_cache) if rx else [])
        if ev:
            channels.append({"name": name, "kind": kind, "evidence": ev[:5]})
    safeguards = {}
    for key, (label, rx, dep_names) in SAFEGUARDS.items():
        ev = _dep_hits(dep_names, deps) + _first_hits(rx, files_cache)
        safeguards[key] = {"label": label, "evidence": ev[:5]}
    risks = {}
    for key, (label, rx) in RISKS.items():
        risks[key] = {"label": label, "evidence": _first_hits(rx, files_cache)}
    kinds = sorted({c["kind"] for c in channels})
    return {"has_communication": bool(channels), "kinds": kinds, "channels": channels,
            "safeguards": safeguards, "risks": risks}


COMM_FEATURES = {"chat", "multiplayer", "social", "ugc"}


def check(name: str, inv: dict, manifest: dict | None):
    """Repository checks built on the inventory. Returns list of (path, line, message)."""
    if not inv["has_communication"]:
        return []
    sg, rk = inv["safeguards"], inv["risks"]
    where = inv["channels"][0]["evidence"][0]
    path, line = _split(where)
    chans = ", ".join(f'{c["name"]} ({c["kind"]})' for c in inv["channels"])
    out = []
    if name == "comms_undeclared":
        declared = set((manifest or {}).get("features") or [])
        if manifest is not None and not (declared & COMM_FEATURES):
            out.append((path, line, f"Communication found in code ({chans}) but no chat, multiplayer, social or ugc feature is declared in cses.yaml."))
    elif name == "comms_report_block":
        if not sg["report"]["evidence"]:
            out.append((path, line, f"Communication found ({chans}) but no reporting function was found in code."))
        if not sg["block"]["evidence"]:
            out.append((path, line, f"Communication found ({chans}) but no block or mute function was found in code."))
    elif name == "comms_moderation":
        if not sg["moderation_role"]["evidence"]:
            out.append((path, line, "No moderator or teacher role with moderation powers (hide, remove, ban, timeout) was found in code."))
        if not sg["auto_filter"]["evidence"]:
            out.append((path, line, "No automated text or image filter (profanity list, moderation API, content safety service) was found."))
    elif name == "comms_direct_messages":
        for ev in rk["direct_messages"]["evidence"][:3]:
            p, ln = _split(ev)
            out.append((p, ln, "Direct or private messaging found: confirm it is limited to pre-approved contacts within the child's group."))
    elif name == "comms_link_filter":
        if any(c["kind"] in ("text chat", "text and voice", "comments", "realtime messaging") for c in inv["channels"]) and not sg["link_filter"]["evidence"]:
            out.append((path, line, "Text communication found but no filtering of links, handles or contact details (phone, email, address) was found."))
    elif name == "comms_voice_video":
        for c in inv["channels"]:
            if c["kind"] in ("voice / video", "text and voice", "live streaming"):
                p, ln = _split(c["evidence"][0])
                out.append((p, ln, f"{c['name']} ({c['kind']}) found: confirm it is off by default, adult-enabled for under-13s, and that children cannot host live streams by default."))
    elif name == "comms_voice_default_on":
        for ev in rk["voice_default_on"]["evidence"][:3]:
            p, ln = _split(ev)
            out.append((p, ln, "Voice or video appears to be on by default."))
    elif name == "comms_media":
        for ev in rk["media_sharing"]["evidence"][:3]:
            p, ln = _split(ev)
            out.append((p, ln, "Images or files can be shared in messages: confirm automated image checks, teacher visibility and no download of children's media by others."))
    elif name == "comms_open_discovery":
        for ev in rk["open_discovery"]["evidence"][:3]:
            p, ln = _split(ev)
            out.append((p, ln, "Contact with unknown users possible (random matching, public rooms or user search)."))
    else:
        raise ValueError(f"Unknown communications check: {name}")
    return out


CHECKS = ["comms_undeclared", "comms_report_block", "comms_moderation", "comms_direct_messages", "comms_link_filter",
          "comms_voice_video", "comms_voice_default_on", "comms_media", "comms_open_discovery"]


def _split(ev: str):
    ev = ev.split(" (dependency")[0]
    m = re.match(r"^(.*):(\d+)$", ev)
    return (m.group(1), int(m.group(2))) if m else (ev, None)


def markdown(inv: dict) -> list[str]:
    if not inv["has_communication"]:
        return ["No communication channels were found in code. If the product has chat, multiplayer or comments "
                "through a service configured outside the repository, declare it in cses.yaml.", ""]
    a = []
    a.append("| Channel | Kind | Evidence |")
    a.append("|---|---|---|")
    for c in inv["channels"]:
        a.append(f"| {c['name']} | {c['kind']} | {', '.join('`' + e + '`' for e in c['evidence'][:3])} |")
    a.append("")
    a.append("| Safeguard | Found in code | Evidence |")
    a.append("|---|---|---|")
    for k, v in inv["safeguards"].items():
        a.append(f"| {v['label']} | {'yes' if v['evidence'] else '**not found**'} | {', '.join('`' + e + '`' for e in v['evidence'][:2])} |")
    a.append("")
    rk = [v for v in inv["risks"].values() if v["evidence"]]
    if rk:
        a.append("| Risk signal | Evidence |")
        a.append("|---|---|")
        for v in rk:
            a.append(f"| {v['label']} | {', '.join('`' + e + '`' for e in v['evidence'][:3])} |")
        a.append("")
    a.append("*A safeguard 'not found' may still exist in a service dashboard or a backend outside this repository. Confirm by hand.*")
    a.append("")
    return a
