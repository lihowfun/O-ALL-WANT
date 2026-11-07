"""Pure catalog functions for OAW skill digestion (prototype v0).

No network, no subprocess and no file writes happen here. Every food byte is
data: it is decoded and pattern-matched, never imported, executed or rendered.

- `normalize_source()` / `dedupe_sources()`: one repository or one paper (every
  arXiv version of it) is one food.
- `static_scan()`: deterministic T0 checks over in-memory files. Static rules
  only raise flags; a "toxic" verdict always needs an owner decision.
- `parse_arxiv_raw()` / `paper_scan()`: a paper's T0 record from its arXiv
  metadata and the sealed PDF's hash; the PDF is never parsed. Components are
  not extracted without a model: that needs the Elephant (planned) or an
  imported digestion record.
- `derive()`: food headline and per-component dispositions from evidence and
  owner decisions. Popularity (stars, author, downloads, requested_by) is not an
  input, and imported reports are historical-prior data that cannot raise it.
- `build_name()`, `install_inventory()`, `effect_vs_default()`, `decide_plan()`
  and `build_view()` feed the CLI and every renderer.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import PurePosixPath
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

SCHEMA_VERSION = 1
RELEASE = "2.0.0"
# 2: inline code spans, imperative commands and any rule match in a SKILL.md body make it X1-inline.
SCANNER_VERSION = 2
VERDICT_RULES_VERSION = 1
# 2: the intake pipeline (stage table plus each food's stage) replaces the four-step track.
# 3: D28: who a food waits on gains `agent` (Claude takes it) and `release` (one decision for the whole branch);
#    agent tastings and D21 absorptions are part of the view.
VIEW_SCHEMA = "oaw-catalog-view/3"

# code: (symbol, ascii, English, Traditional Chinese)
VERDICTS = {
    "nutritious": ("●", "[+]", "nutritious", "營養"),
    "no-gain": ("＝", "[=]", "no gain", "沒營養"),
    "untested": ("○", "[ ]", "untested", "未測"),
    "incomplete": ("◌", "[?]", "incomplete evidence", "證據不完整"),
    "regressed": ("▼", "[v]", "regressed", "變差"),
    "diarrhea": ("◐", "[~]", "diarrhea", "拉肚子"),
    "risky": ("▲", "[!]", "risky", "有疑慮"),
    "toxic": ("✖", "[X]", "toxic", "有毒"),
    "inedible": ("⊘", "[/]", "inedible", "不能吃"),
}
HEADLINE_PRIORITY = ("toxic", "inedible", "risky", "regressed", "diarrhea", "incomplete", "no-gain", "nutritious", "untested")
EVIDENCE_LEVELS = {
    "measured": "measured by a consented live run",
    "static-measured": "measured from files without running anything",
    "not-measured": "not measured",
    "historical-prior": "imported historical report; never counted in a verdict",
}
EVIDENCE_LEVELS_ZH = {"measured": "實測", "static-measured": "靜態量測", "not-measured": "未量測", "historical-prior": "歷史證據"}
LIVE_PROVENANCE = ("runner-live", "operator-run")
DISPOSITIONS = {"absorb": ("green", "吸收"), "excrete": ("red", "排掉"), "hold": ("amber", "暫留")}
DECISION_KINDS = ("triage", "absorb", "excrete", "remove", "block", "reject")
TRIAGE_OUTCOMES = ("benign", "allergen", "confirm-toxic")
POPULARITY_FIELDS = ("stars", "stargazers_count", "author", "downloads", "requested_by", "official", "forks",
                     "watchers", "popularity", "scout", "intake")
# Size never stops a food (owner, 2026-11-06: "snapshot exceeds 50 MB 限制沒有任何意義"). The caps only bound what is
# stored and scanned: past them the largest files are skipped and flagged F-PARTIAL; the food is still tasted.
LIMITS = {"max_files": 20000, "max_total_bytes": 200 * 1024 * 1024, "max_file_bytes": 5 * 1024 * 1024,
          "max_path": 240, "skill_body_bytes": 24000, "max_download_bytes": 400 * 1024 * 1024}
TOKENS_PER_RUN = (600_000, 900_000)
TOKEN_LABEL = "estimate: about 0.6-0.9M logical tokens per tool-using agent run"
TOKEN_LABEL_ZH = "估計：每次會用工具的 agent run 約 0.6–0.9M 邏輯 tokens"
# Names a food id must never take: `remove egm` and bundled skill names mean the bundled parts.
RESERVED_FOOD_IDS = ("egm", "egm-bootstrap", "egm-brainstorm", "egm-draft", "egm-drift-report", "egm-resolve", "egm-review",
                     "egm-review-loop", "oaw-evidence", "oaw-review", "oaw-wiki", "oaw-improve", "oaw")
SANDBOX_CONDITIONS = ("isolated-venv", "project-copy", "no-api-keys", "no-network", "disposable-vm")
INSTALL_ALLOWED_SUFFIXES = (".md", ".txt")
ROUTER_NAMES = ("claude.md", "agents.md", "gemini.md", ".cursorrules", ".windsurfrules", "copilot-instructions.md")
READ_ONLY_TOOLS = {"read", "grep", "glob", "ls"}

_HEX64 = re.compile(r"[0-9a-f]{64}")
_UNSAFE_TEXT = re.compile("[\x00-\x1f\x7f-\x9f\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff"
                          "\U000e0000-\U000e007f]")
_HIDDEN = re.compile("[\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0000-\U000e007f]")
_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}


class SourceError(ValueError):
    """An input that is not a supported food source."""


# Known engine messages (English, for logs and the CLI) -> Traditional Chinese for the page and the menu.
# A message that matches nothing keeps its English text; renderers then say so.
ERRORS_ZH = (
    (r"The weekly cap must be at least the per-food cap", "每週上限必須至少等於每樣食物的上限。"),
    (r"Token caps must be whole numbers", "token 上限必須是 0 到 10^10 之間的整數。"),
    (r"Sandbox conditions must be a nonempty subset", "試跑條件至少要勾一個，而且只能用列出的條件。"),
    (r"Only (?:github\.com repositories|GitHub repositories and arXiv papers) are supported", "只支援 GitHub 上的 repo 和 arXiv 論文。"),
    (r"Not a (?:GitHub )?repository(?: or arXiv paper)?(?: URL)?", "這不是 GitHub repo 或 arXiv 論文的網址。"),
    (r"Not an arXiv paper URL", "這不是 arXiv 論文的網址：請用 arxiv.org/abs/編號、arxiv.org/pdf/編號 或 arXiv:編號。"),
    (r"Invalid arXiv identifier", "arXiv 編號的格式不對（例如 2606.03979、2606.03979v2 或 hep-th/9901001）。"),
    (r"URL lacks OWNER/REPO", "網址缺少「擁有者/repo」。"),
    (r"Invalid GitHub OWNER/REPO", "GitHub 的「擁有者/repo」格式不對。"),
    (r"Only local file:// repository (?:or PDF )?paths|Unsafe file:// (?:repository )?path", "只接受本機的 file:// repo 或 PDF 路徑。"),
    (r"git fetch failed", "抓不到這個 repo（git fetch 失敗）：網址打錯、repo 不存在，或連不上。"),
    (r"Tarball download failed", "下載備用壓縮檔失敗：連不上 GitHub。"),
    (r"Paper download failed", "下載論文失敗：連不上 arXiv，或逾時。"),
    (r"arXiv has no record", "arXiv 查不到這篇論文（編號打錯，或還沒公開）。"),
    (r"arXiv lists no version", "arXiv 沒有這個版本：用 show 看有哪些版本，或不指定版本（固定最新版）。"),
    (r"arXiv metadata is not readable|arXiv answered for a different paper", "讀不懂 arXiv 回傳的中繼資料：沒有封存任何東西。"),
    (r"Refused: only https|Refused: a redirect", "拒收：只接受 https 和 arXiv 的網址（轉址也一樣）。"),
    (r"is not a PDF", "拒收：抓到的不是 PDF（開頭不是 %PDF-）：沒有封存任何東西。"),
    (r"Cannot read the local PDF", "讀不到這個本機 PDF。"),
    (r"A paper's --ref", "論文的版本要寫成 v1、v2 這種格式。"),
    (r"is a paper: a paper's ideas are absorbed by re-implementing",
     "論文不走複製文字的吸收：論文的想法要重新實作成 OAW 程式和測試（D5、D21），不複製原文；匯入的歷史提案仍可記成待辦。"),
    (r"Cannot fetch", "抓不到這個 repo。"),
    (r"Refused: .*(?:limit|too many files)|exceeds the archive limits", "拒收：超過封存的大小或檔案數上限。"),
    (r"Integrity failure", "完整性檢查失敗：同一個版本抓到不同的內容，保留原本的封存。"),
    (r"Unknown food", "找不到這樣食物。"),
    (r"needs an interactive terminal", "這一步要你本人在互動式終端機上確認（PowerShell／cmd，或 Git Bash 裡用 winpty）。"),
    (r"confirmation code does not match|confirmation code has expired|No pending .* confirmation|code was refused",
     "確認碼不對或已過期（每個碼只能試一次）：請重新送出取得新的碼。"),
    (r"Too many wrong confirmation codes", "確認碼錯太多次：這次啟動不再接受確認，請重新啟動 catalog.py ui 或 menu。"),
    (r"a confirmation code was shown on the terminal", "確認碼已印在終端機上。"),
    (r"A (?:triage|removal) reason is required|reason is required", "請寫下原因（會記進決定紀錄）。"),
    (r"Restore would overwrite", "還原會蓋掉不屬於目前安裝層的檔案（你自己的或自訂的檔案）：先移開或改名，或留在目前版本。"),
    (r"not a restore point this LAB_HOME created|restore point is missing|outside the OAW-managed layer|lacks a valid install manifest",
     "這個還原點不是這台電腦替這個專案建立的，或內容超出 OAW 安裝層：已拒絕，沒有還原。"),
    (r"Edited files block|Edited absorbed files are protected", "你改過的檔案擋住了這個動作：先用 oaw.py migrate 處理。"),
    (r"fails OAW's portable skill lint|would fail doctor", "這個 skill 不符合 OAW 的 skill 格式（doctor 會判失敗）：沒有安裝。"),
    (r"already absorbed", "這個成分已經吸收過了。"),
    (r"only parts proposed for absorption", "只有建議「吸收」的成分可以吸收。"),
    (r"Install target already exists", "要安裝的位置已經有檔案：沒有覆蓋。"),
    (r"is not in the installed recipe", "目前的安裝裡沒有這個 skill。"),
    (r"is already installed", "這個 skill 已經裝著了。"),
    (r"A removal never adds|A re-add never retires", "這個變更會順帶新增或停用別的 skill：已拒絕。"),
    (r"receipt lists a path outside", "吸收收據列了 skill 資料夾以外的檔案：已拒絕，沒有刪除任何東西。"),
    (r"No OAW install", "這個資料夾還沒有安裝 OAW：先執行 oaw.py init。"),
    (r"LAB_HOME must be outside", "LAB_HOME 必須在專案和 OAW 框架之外：設定 OAW_LAB_HOME。"),
    (r"has absorbed parts; remove them first", "這樣食物還有吸收中的成分：先移除，再忘掉它。"),
    (r"was removed; re-adding it needs a new taste", "這個成分移除過：再加回要先重新試吃（免費），才能再吸收（D6）。"),
    (r"Report directory not found|No digestion records", "找不到報告資料夾，或資料夾裡沒有消化紀錄。"),
    (r"Scout could not reach GitHub", "偵查連不上 GitHub 搜尋。"),
    (r"A question is at most", "問題太長：最多 500 字。"),
    (r"A question is empty", "問題是空的：先寫下你想問什麼。"),
    (r"Too many open questions", "問題已經記滿了，而且都還沒回答：先在對話裡處理，再用 catalog.py questions --answered 編號 標成已回答。"),
    (r"food, stage and question must be text", "要寫明哪樣食物、哪一站和問題的文字。"),
    (r"Unknown pipeline stage", "沒有這一站。"),
    (r"Unknown question", "找不到這個問題編號。"),
    (r"no verdict without the food arm", "拒收：食物組沒有任何評分過的執行，就不能有判定（D28）；請記成 no-verdict，寫明卡在哪裡。"),
    (r"A no-verdict tasting must say", "沒有判定的試吃要寫明卡在哪裡（blocked_on_owner 或 notes）。"),
    (r"A tier-B unit", "B 級單位（模型會讀的文字）要有這樣食物判定「吸收」的試吃紀錄才能記成吸收（D17、D21）。"),
    (r"A tier-C unit", "C 級單位要先由你決定（D21）：記成暫留並寫 blocked_on_owner，或在 owner_approval 寫明你在哪裡同意的。"),
    (r"Not a tasting record|Not an absorption record", "這不是 OAW 的試吃或吸收紀錄（schema 不對）。"),
    (r"names another food", "紀錄裡寫的食物和 --food 不同：沒有記錄。"),
    (r"(?:tasting|absorption) record file", "讀不到紀錄檔，或它不是 1 MB 以內的 JSON。"),
    (r"^(?:Tasting|Absorption) record: ", "紀錄的欄位不對：沒有記錄（原文見英文訊息）。"),
)


def zh_error(message) -> str | None:
    """Traditional Chinese for a known engine message, or None."""
    text = str(message or "")
    for pattern, chinese in ERRORS_ZH:
        if re.search(pattern, text):
            return chinese
    return None


# Verdict reasons derive() writes (English) -> Traditional Chinese; an unknown reason keeps its English text.
REASONS_ZH = (
    (r"^no static record \(taste not run\)$", lambda m: "沒有靜態紀錄（還沒試吃）"),
    (r"^owner-confirmed: (.+)$", lambda m: "你確認有毒：" + m.group(1)),
    (r"^(\d+) high-severity flag\(s\) not triaged$", lambda m: f"{m.group(1)} 個高嚴重度旗標還沒分流"),
    (r"^owner (?:block|reject): ?(.*)$", lambda m: "你擋下了這樣食物：" + m.group(1)),
    (r"^no measured evidence \(paid tests not run\)$", lambda m: "沒有實測證據（付費實測還沒跑）"),
    (r"^measured regression$", lambda m: "實測變差"),
    (r"^unconfirmed-negative", lambda m: "未確認的負面結果：只有一組；不能吸收，也沒證明有害"),
    (r"^measured evidence is incomplete$", lambda m: "實測證據不完整"),
    (r"^no gain observed under this specification$", lambda m: "這個規格下沒有觀察到增益"),
    (r"^harms the current recipe$", lambda m: "會傷到現有配方"),
    (r"^integration-not-complete$", lambda m: "整合檢查還沒完成"),
    (r"^parity-floor-not-run$", lambda m: "齊平底線還沒跑"),
    (r"^measured gain with parity floor$", lambda m: "實測有增益，也過了齊平底線"),
)
# Static flag rule -> Traditional Chinese meaning (the English meaning stays in the record).
FLAG_MEANINGS_ZH = {
    "F-PIPE": "把下載的內容直接交給 shell 執行", "F-EXEC": "執行解碼或下載來的程式碼",
    "F-HOST": "動到 host agent 設定或 MCP 註冊", "F-GLOBAL": "動到使用者的全域設定", "F-UPDATE": "自己更新或安裝軟體",
    "F-BG": "啟動背景或排程的行程", "F-WRITE-INSTR": "寫入 agent 指示檔", "S-HOME": "提到家目錄", "S-NET": "網路功能",
    "S-MODEL": "自己呼叫模型", "S-DEP": "自動執行的指令用了沒固定版本的套件", "S-HOOK": "宣告會自動執行的 hooks",
    "S-HOOK-CTX": "hooks 會把內容寫進 context", "S-MCP": "宣告 MCP server", "S-LIFECYCLE": "安裝時會執行套件腳本",
    "F-HID": "隱藏或雙向控制字元", "S-SHADOW": "放在 sys.path 上時，Python import 或啟動時就會執行",
    "S-BUILD": "安裝時會執行 build backend 的程式碼", "S-NEST": "巢狀的常駐指示檔", "F-LINK": "記錄了 symlink，沒有跟進",
    "F-ARC": "記錄了 submodule，沒有抓取", "F-PARTIAL": "超過大小上限的檔案沒有存，也沒有掃描",
    "S-EXCL": "屬於 V2 排除的類別（你解除之前只能放在本機）", "S-LIC": "沒有認得的授權：不能確定可以轉發",
    "S-BUD": "skill 本文超過大小上限",
    "P-LIC": "只取想法：授權不允許轉用原文，要重新實作，不複製文字",
}


def reason_zh(reason) -> str:
    text = str(reason or "")
    for pattern, render in REASONS_ZH:
        match = re.match(pattern, text)
        if match:
            return render(match)
    return text


# --------------------------------------------------------------------------- hashing / text

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def record_sha256(value) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def tree_sha256(file_hashes: dict) -> str:
    """Hash of sorted "<sha256>  <path>" lines over the received bytes."""
    return sha256_bytes("".join(f"{h}  {p}\n" for p, h in sorted(file_hashes.items())).encode("utf-8"))


def sanitize_text(value, limit: int = 200) -> str:
    """Food-derived text for terminals and HTML builders: no controls, bidi or zero-width."""
    text = _UNSAFE_TEXT.sub(" ", unicodedata.normalize("NFC", str(value if value is not None else "")))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def display_name(name: str) -> str:
    return name if isinstance(name, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) else "id#" + sha256_bytes(str(name).encode())[:8]


def slug(value: str, limit: int = 64) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).casefold()).strip("-")
    return (text[:limit].strip("-") or "food")


def _normalized(text: str) -> str:
    """Matching form: NFKC, casefold, format (Cf) characters removed."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


# --------------------------------------------------------------------------- sources

_ARXIV_ID = re.compile(r"(?i)(?:(?P<yymm>\d{4})\.(?P<seq>\d{4,5})|(?P<archive>[a-z]+(?:-[a-z]+)?)(?:\.[a-z]{2})?/(?P<num>\d{7}))"
                       r"(?:v(?P<version>[1-9]\d{0,3}))?")


def arxiv_identity(text: str) -> tuple:
    """(canonical arXiv id, version or None) for `2606.03979v2` or old-style `hep-th/9901001v1`."""
    match = _ARXIV_ID.fullmatch(str(text or ""))
    if match and match.group("yymm"):
        yymm, seq = match.group("yymm"), match.group("seq")
        # Four-digit sequence numbers end with 1412; five-digit ones start with 1501.
        valid = 1 <= int(yymm[2:]) <= 12 and (len(seq) == 5) == (yymm >= "1501")
        arxiv_id = f"{yymm}.{seq}"
    elif match:
        valid = 1 <= int(match.group("num")[2:4]) <= 12
        # The canonical old-style id drops the subject class: math.GT/0309136 is math/0309136.
        arxiv_id = f"{match.group('archive').casefold()}/{match.group('num')}"
    else:
        valid = False
    if not valid:
        raise SourceError(f"Invalid arXiv identifier: {sanitize_text(text, 80)!r}")
    return arxiv_id, ("v" + match.group("version") if match.group("version") else None)


def _arxiv_source(raw: str):
    """A paper source for `arXiv:ID`, `arxiv.org/abs/ID` or `arxiv.org/pdf/ID[.pdf]` (any version); None otherwise."""
    match = re.fullmatch(r"(?i)arxiv:(.+)", raw)
    if match:
        ident = match.group(1)
    elif re.match(r"(?i)^(?:https?://)?(?:www\.|export\.)?arxiv\.org(?:[/?#]|$)", raw):
        parts = urlsplit(raw if "://" in raw else "https://" + raw)
        segments = [unquote(s) for s in parts.path.split("/") if s]
        if len(segments) < 2 or segments[0].casefold() not in ("abs", "pdf"):
            raise SourceError(f"Not an arXiv paper URL (use arxiv.org/abs/ID or arxiv.org/pdf/ID): {sanitize_text(raw, 80)!r}")
        ident = "/".join(segments[1:])
        if segments[0].casefold() == "pdf" and ident.casefold().endswith(".pdf"):
            ident = ident[:-4]
    else:
        return None
    arxiv_id, version = arxiv_identity(ident)
    # The key has no version, so v1 and v2 are one food; the requested version is kept as the ref.
    return {"key": f"arxiv.org/{arxiv_id}", "kind": "paper", "owner": None, "repo": "arxiv-" + arxiv_id.replace("/", "-"),
            "display": f"arXiv:{arxiv_id}", "url": f"https://arxiv.org/abs/{arxiv_id}",
            "fetch_url": f"https://arxiv.org/pdf/{arxiv_id}{version or ''}", "ref": version, "subdir": None, "arxiv_id": arxiv_id}


def is_local_source(source: dict) -> bool:
    """A local repository or PDF: its path is private, so records name it by a private reference."""
    return source.get("kind") == "file" or str(source.get("key") or "").startswith("file://")


def normalize_source(text: str) -> dict:
    """Canonical identity of a food source. The key ignores case, .git, slashes and refs.

    Accepted: GitHub repositories, arXiv papers (`arXiv:ID`, `arxiv.org/abs/ID`, `arxiv.org/pdf/ID`), and local
    `file://` git repositories or PDFs.
    """
    raw = str(text or "").strip()
    if not raw or len(raw) > 512 or any(ch.isspace() for ch in raw) or _UNSAFE_TEXT.search(raw):
        raise SourceError(f"Not a GitHub repository or arXiv paper URL: {sanitize_text(raw, 80)!r}")
    if raw.casefold().startswith("file://"):
        parts = urlsplit(raw)
        if parts.netloc not in ("", "localhost") or parts.query or parts.fragment:
            raise SourceError("Only local file:// repository or PDF paths are supported.")
        path = unquote(parts.path).rstrip("/")
        if not path or ".." in path.split("/"):
            raise SourceError("Unsafe file:// path.")
        name = path.rsplit("/", 1)[-1]
        key = "file://" + path
        if name.casefold().endswith(".pdf"):
            return {"key": key, "kind": "paper", "owner": None, "repo": name[:-4] or "paper", "display": "local/" + name,
                    "url": key, "fetch_url": key, "ref": None, "subdir": None, "arxiv_id": None}
        name = name[:-4] if name.casefold().endswith(".git") and len(name) > 4 else name
        return {"key": key, "kind": "file", "owner": None, "repo": name, "display": "local/" + name,
                "url": key, "fetch_url": "file://" + path, "ref": None, "subdir": None}
    paper = _arxiv_source(raw)
    if paper:
        return paper
    ref = subdir = None
    match = re.fullmatch(r"(?i)git@github\.com:([^/]+)/([^/]+?)/?", raw)
    if match:
        owner, repo, rest = match.group(1), match.group(2), []
    else:
        if re.match(r"(?i)^(?:https?|ssh|git)://", raw):
            parts = urlsplit(raw)
        elif re.match(r"(?i)^(?:www\.)?github\.com/", raw):
            parts = urlsplit("https://" + raw)
        elif re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+/?", raw):
            parts = urlsplit("https://github.com/" + raw)
        else:
            raise SourceError(f"Not a GitHub repository or arXiv paper: {sanitize_text(raw, 80)!r}")
        if parts.scheme.casefold() not in ("https", "http", "ssh", "git") or (parts.hostname or "").casefold() not in ("github.com", "www.github.com"):
            raise SourceError(f"Only GitHub repositories and arXiv papers are supported: {sanitize_text(raw, 80)!r}")
        segments = [unquote(s) for s in parts.path.split("/") if s]
        if len(segments) < 2:
            raise SourceError(f"URL lacks OWNER/REPO: {sanitize_text(raw, 80)!r}")
        owner, repo, rest = segments[0], segments[1], segments[2:]
    if repo.casefold().endswith(".git"):
        repo = repo[:-4]
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repo) or repo in (".", ".."):
        raise SourceError(f"Invalid GitHub OWNER/REPO: {sanitize_text(owner + '/' + repo, 80)!r}")
    if len(rest) >= 2 and rest[0] in ("tree", "blob") and re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", rest[1]):
        ref = rest[1]
        subdir = "/".join(rest[2:]) or None
    return {"key": f"github.com/{owner.casefold()}/{repo.casefold()}", "kind": "github", "owner": owner, "repo": repo,
            "display": f"{owner}/{repo}", "url": f"https://github.com/{owner}/{repo}",
            "fetch_url": f"https://github.com/{owner}/{repo}.git", "ref": ref, "subdir": subdir}


def dedupe_sources(inputs) -> dict:
    """Group a batch by canonical key; report merges and unusable inputs."""
    foods, errors = {}, []
    for item in inputs:
        try:
            source = normalize_source(item)
        except SourceError as exc:
            errors.append({"input": sanitize_text(item, 120), "error": str(exc), "error_zh": zh_error(exc)})
            continue
        entry = foods.setdefault(source["key"], {"source": source, "inputs": [], "ignored": []})
        entry["inputs"].append(str(item).strip())
        # The first spelling defines the food; a different ref or subdirectory in a later one is reported, not adopted.
        kept = entry["source"]
        for field in ("ref", "subdir"):
            if source[field] and source[field] != kept[field] and {"field": field, "value": source[field]} not in entry["ignored"]:
                entry["ignored"].append({"field": field, "value": sanitize_text(source[field], 120)})
    merges = []
    for key, entry in foods.items():
        if len(entry["inputs"]) > 1:
            merge = {"key": key, "inputs": entry["inputs"]}
            if entry["ignored"]:
                merge["ignored"] = entry["ignored"]
            merges.append(merge)
    return {"foods": [{"source": e["source"], "inputs": e["inputs"]} for e in foods.values()], "merges": merges, "errors": errors}


def food_id(source: dict, taken: dict) -> str:
    """Short, stable registry id; `taken` maps existing ids to canonical keys.

    A repository named like a bundled part (egm, oaw-evidence, ...) gets an
    owner-qualified id, so `remove egm` can never mean a food.
    """
    for candidate in (slug(source["repo"]), slug(f"{source.get('owner') or 'local'}-{source['repo']}")):
        if candidate in RESERVED_FOOD_IDS:
            continue
        if taken.get(candidate) in (None, source["key"]):
            return candidate
    return slug(source["repo"], 55) + "-" + sha256_bytes(source["key"].encode())[:8]


# --------------------------------------------------------------------------- archive members

def member_path_error(path: str, seen_casefold: set | None = None):
    """Why a food path cannot enter the sealed tar, or None."""
    if not isinstance(path, str) or not path:
        return "empty path"
    if len(path) > LIMITS["max_path"]:
        return "path too long"
    if "\\" in path or ":" in path or path.startswith("/") or _UNSAFE_TEXT.search(path):
        return "unsafe characters"
    for part in path.split("/"):
        if part in ("", ".", ".."):
            return "unsafe segment"
        if part.split(".")[0].casefold() in _RESERVED or part.rstrip(". ") != part:
            return "reserved Windows name"
    if seen_casefold is not None:
        folded = path.casefold()
        if folded in seen_casefold:
            return "case collision"
        seen_casefold.add(folded)
    return None


# --------------------------------------------------------------------------- T0 static checks

_SCRIPT_SUFFIXES = {".py", ".pyw", ".sh", ".bash", ".zsh", ".fish", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts",
                    ".tsx", ".jsx", ".ps1", ".psm1", ".bat", ".cmd", ".rb", ".pl", ".php", ".lua", ".go", ".rs",
                    ".java", ".kt", ".swift", ".c", ".cc", ".cpp", ".cs", ".vbs", ".pth"}
_CONFIG_SUFFIXES = {".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".env", ".lock"}
_DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc", ".org"}
_ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp", ".pdf", ".woff", ".woff2",
                   ".ttf", ".otf", ".mp3", ".mp4", ".wav", ".webm", ".mov", ".zip", ".gz", ".tgz"}
_MANIFESTS = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "pyproject.toml",
              "setup.py", "setup.cfg", "pipfile", "pipfile.lock", "poetry.lock", "uv.lock", "cargo.toml",
              "cargo.lock", "go.mod", "go.sum", "gemfile", "gemfile.lock", "composer.json", "dockerfile",
              "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "makefile", "deno.json"}
_BINARY_MAGIC = (b"\x7fELF", b"\0asm", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xfe\xed\xfa\xce", b"\xca\xfe\xba\xbe")
_IMPORT_HOOKS = {"sitecustomize.py", "usercustomize.py", "conftest.py"}

_HOST_SETTINGS = r"\.claude/settings(?:\.local)?\.json|\.claude\.json\b|\.codex/(?:config\.toml|hooks\.json)|\b(?:claude|codex)\s+mcp\s+add\b|\.mcp\.json\b"
_GLOBAL = r"git\s+config\s+--global|npm\s+config\s+set|\.bashrc\b|\.zshrc\b|\.bash_profile\b|\bsetx\s|\.gitconfig\b"
_HOME = r"(?:^|[\s\"'(=])~/|\$home\b|%userprofile%|%appdata%|\$env:userprofile|expanduser\(|path\.home\(\)|os\.homedir\(\)"
_UPDATE = (r"\bgit\s+pull\b|\bnpm\s+(?:update|i(?:nstall)?\s+(?:-g|--global))\b|\bpip3?\s+install\s+(?:-u\b|--upgrade)"
           r"|\buv\s+tool\s+(?:install|upgrade)\b|\bself[-_ ]?update\b|\bauto[-_ ]?updat\w*|\bbrew\s+upgrade\b")
_BACKGROUND = (r"\bnohup\b|\bsetsid\b|\bdisown\b|\bstart\s+/b\b|start_new_session\s*=\s*true|detached\s*:\s*true"
               r"|\bpm2\s+start\b|\bdaemoni[sz]e\b|\bdaemon\s*[:=]\s*true|\bsystemctl\s+(?:enable|start)\b|\blaunchctl\b|\bcrontab\b|\bschtasks\b")
_NETWORK = (r"\b(?:curl|wget)\b|urllib\.request|\brequests\.(?:get|post|put|patch|delete|session)\b|http\.client"
            r"|\bfetch\s*\(|\baxios\b|socket\.socket|invoke-webrequest|invoke-restmethod|\bhttpx\b|\baiohttp\b|xmlhttprequest|\bwebsocket\b"
            r"|^\s*(?:import|from)\s+(?:requests|httpx|aiohttp|urllib3|websockets?)\b")
_MODEL = (r"\bclaude\s+-p\b|\bcodex\s+exec\b|api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com"
          r"|^\s*(?:import|from)\s+(?:anthropic|openai|litellm)\b|@anthropic-ai/(?:sdk|claude-agent-sdk|claude-code)|require\(['\"]openai['\"]\)")
_WRITE_INSTRUCTIONS = r"\b(?:append|write|add|insert|inject|update)\w*\b[^\n]{0,60}\b(?:claude|agents|gemini)\.md\b"
_PIPE = r"\b(?:curl|wget|iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b|\|\s*iex\b"
_EXEC = (r"\b(?:eval|exec)\s*\(\s*(?:base64|b64decode|atob|codecs\.decode|bytes\.fromhex|zlib\.decompress|requests\.|urllib|fetch\s*\()"
         r"|base64\s+(?:-d|--decode)\b[^\n]*\|\s*(?:ba)?sh\b|__import__\(\s*['\"]base64")

_SEV = {
    "critical": {"auto-exec": "high", "executable": "high", "instruction": "high", "manifest": "high", "config": "medium", "other": "medium"},
    "host": {"auto-exec": "high", "executable": "high", "instruction": "medium", "manifest": "medium", "config": "medium", "other": "low"},
    "behaviour": {"auto-exec": "high", "executable": "medium", "instruction": "medium", "manifest": "medium", "config": "low", "other": "low"},
    "surface": {"auto-exec": "medium", "executable": "low", "instruction": "low", "manifest": "low", "config": "low", "other": "low"},
}
# (rule, pattern, severity table, allergen, meaning)
RULES = (
    ("F-PIPE", _PIPE, "critical", "network", "pipes a download into a shell"),
    ("F-EXEC", _EXEC, "critical", None, "executes decoded or downloaded code"),
    ("F-HOST", _HOST_SETTINGS, "host", "host-settings", "touches host agent settings or MCP registration"),
    ("F-GLOBAL", _GLOBAL, "host", "writes-outside-project", "touches global user configuration"),
    ("F-UPDATE", _UPDATE, "behaviour", "auto-update", "updates or installs software by itself"),
    ("F-BG", _BACKGROUND, "behaviour", "background-process", "starts a background or scheduled process"),
    ("F-WRITE-INSTR", _WRITE_INSTRUCTIONS, "behaviour", "writes-instructions", "writes agent instruction files"),
    ("S-HOME", _HOME, "surface", "writes-outside-project", "refers to the home directory"),
    ("S-NET", _NETWORK, "surface", "network", "network primitive"),
    ("S-MODEL", _MODEL, "surface", "spawns-model-calls", "calls a model by itself"),
)
_COMPILED = tuple((rule, re.compile(pattern, re.MULTILINE), table, allergen, meaning) for rule, pattern, table, allergen, meaning in RULES)
_ANY_RULE = re.compile("|".join(f"(?:{pattern})" for _rule, pattern, *_ in RULES), re.MULTILINE)
EXCLUSIONS = {
    "vector-db": ("chromadb", "faiss", "faiss-cpu", "faiss-gpu", "lancedb", "qdrant-client", "pgvector", "weaviate-client",
                  "pymilvus", "pinecone", "pinecone-client", "sqlite-vec", "sqlite-vss", "hnswlib", "usearch", "@lancedb/lancedb",
                  "chromadb-client", "vectordb"),
    "graph-memory": ("neo4j", "kuzu", "falkordb", "graphiti", "graphiti-core", "memgraph", "py2neo"),
    "second-model-runtime": ("ollama", "llama-cpp-python", "llama_cpp", "vllm", "transformers", "torch", "onnxruntime",
                             "sentence-transformers", "mlx", "ctransformers", "gpt4all", "node-llama-cpp", "@xenova/transformers"),
}
SKILL_CHECKS = ("S-ID", "S-ROLE", "S-LIC", "S-STR", "S-KIND", "S-DEP", "S-MODEL", "S-EXCL", "S-FLAG", "S-NET", "S-BUD", "S-HOOK", "S-MCP", "S-NEST", "S-SHADOW")


def file_role(path: str, data: bytes, mode: str | None = None) -> str:
    """S-ROLE: binary, instruction, manifest, executable, config, docs, asset or other."""
    pure = PurePosixPath(path)
    name, suffix = pure.name.casefold(), pure.suffix.casefold()
    parents = [p.casefold() for p in pure.parts[:-1]]
    if data.startswith(_BINARY_MAGIC) or data[:2] == b"MZ" and suffix in ("", ".exe", ".dll", ".bin"):
        return "binary"
    if suffix in _ASSET_SUFFIXES:
        return "asset"
    if b"\0" in data[:8192]:
        return "binary"
    if name == "skill.md" or name in ROUTER_NAMES or (suffix == ".md" and parents and parents[-1] in ("agents", "commands")):
        return "instruction"
    if name in _MANIFESTS or re.fullmatch(r"requirements[\w.-]*\.txt", name):
        return "manifest"
    if mode == "100755" or data.startswith(b"#!") or suffix in _SCRIPT_SUFFIXES:
        return "executable"
    if suffix in _CONFIG_SUFFIXES:
        return "config"
    if (suffix in _DOC_SUFFIXES or (parents and parents[0] in ("docs", "doc")) or
            re.match(r"(?:readme|license|licence|copying|notice|changelog|contributing|authors|security)\b", name)):
        return "docs"
    return "other"


def parse_frontmatter(text: str):
    """Restricted YAML subset: top-level `key: value` and folded/literal blocks."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text
    fields, key = {}, None
    for line in lines[1:end]:
        match = re.match(r"([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if match and not line[:1].isspace():
            key, value = match.group(1).casefold(), match.group(2).strip()
            fields[key] = "" if value in ("|", ">", "|-", ">-") else value.strip("'\"")
        elif key and line[:1].isspace():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, "\n".join(lines[end + 1:])


def detect_license(files: dict) -> dict:
    """S-LIC: normalized license text against a few SPDX signatures."""
    candidates = sorted(p for p in files if "/" not in p and re.match(r"(?i)(?:license|licence|copying|unlicense)(?:[.-].*)?$", p))
    signatures = (
        ("AGPL-3.0", ("gnu affero general public license",)), ("LGPL-3.0", ("gnu lesser general public license",)),
        ("GPL-3.0", ("gnu general public license", "version 3")), ("GPL-2.0", ("gnu general public license", "version 2")),
        ("Apache-2.0", ("apache license", "version 2.0")), ("MPL-2.0", ("mozilla public license",)),
        ("MIT", ("permission is hereby granted, free of charge",)),
        ("BSD-3-Clause", ("redistribution and use in source and binary forms", "neither the name")),
        ("BSD-2-Clause", ("redistribution and use in source and binary forms",)),
        ("ISC", ("permission to use, copy, modify, and/or distribute this software",)),
        ("Unlicense", ("this is free and unencumbered software",)),
    )
    found = []
    for path in candidates:
        text = re.sub(r"\s+", " ", _normalized(files[path].decode("utf-8", "replace")))
        for spdx, needles in signatures:
            if all(needle in text for needle in needles):
                found.append({"spdx": spdx, "file": path, "sha256": sha256_bytes(files[path])})
                break
        else:
            found.append({"spdx": "unknown", "file": path, "sha256": sha256_bytes(files[path])})
    permissive = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC", "Unlicense", "MPL-2.0"}
    known = [item for item in found if item["spdx"] != "unknown"]
    if not found:
        return {"spdx": None, "files": [], "distribution": "unknown"}
    spdx = " AND ".join(sorted({item["spdx"] for item in known})) or "unknown"
    distribution = ("redistributable" if known and all(i["spdx"] in permissive for i in known)
                    else "local-only" if known else "unknown")
    return {"spdx": spdx, "files": found, "distribution": distribution}


def _json(data: bytes):
    try:
        value = json.loads(data.decode("utf-8-sig"))
    except (ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def _hook_commands(config: dict):
    """Yield (event, command) from Claude/Codex style hooks objects."""
    hooks = config.get("hooks", config)
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            inner = group.get("hooks") if isinstance(group.get("hooks"), list) else [group]
            for hook in inner:
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    yield str(event), hook["command"]


def _declared_deps(path: str, data: bytes) -> list:
    name = PurePosixPath(path).name.casefold()
    text = data.decode("utf-8", "replace")
    found = []
    if name == "package.json":
        value = _json(data) or {}
        for field in ("dependencies", "peerDependencies", "optionalDependencies"):
            if isinstance(value.get(field), dict):
                found.extend((dep, str(spec)) for dep, spec in value[field].items())
    elif re.fullmatch(r"requirements[\w.-]*\.txt", name):
        for line in text.splitlines():
            match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)(.*)", line)
            if match and not line.lstrip().startswith(("#", "-")):
                found.append((match.group(1), match.group(2).strip()))
    elif name in ("pyproject.toml", "setup.py", "setup.cfg"):
        block = re.search(r"(?:^|\n)\s*(?:dependencies|install_requires)\s*=\s*\[(.*?)\]", text, re.S)
        for item in re.findall(r"['\"]([A-Za-z0-9][A-Za-z0-9._-]*)([^'\"]*)['\"]", block.group(1) if block else ""):
            found.append(item)
    return [(dep.casefold().replace("_", "-"), spec) for dep, spec in found]


def _code_imports(path: str, text: str) -> set:
    suffix = PurePosixPath(path).suffix.casefold()
    names = set()
    if suffix in (".py", ".pyw"):
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names.add(node.module.split(".")[0])
    elif suffix in (".js", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".tsx", ".jsx"):
        for match in re.finditer(r"(?:require\(\s*|\bfrom\s+|\bimport\s+)['\"]([^'\"./][^'\"]*)['\"]", text):
            spec = match.group(1)
            names.add("/".join(spec.split("/")[:2]) if spec.startswith("@") else spec.split("/")[0])
    return {name.casefold().replace("_", "-") for name in names if name}


def _command_paths(command: str, paths) -> set:
    """Files a hook/MCP/lifecycle command refers to (suffix match, never resolved on disk)."""
    referenced = set()
    for token in re.findall(r"[\w${}.@%/\\-]+\.(?:sh|bash|py|js|mjs|cjs|ts|ps1|bat|cmd|rb|pl)\b", command):
        token = re.sub(r"^(?:\$\{[^}]+\}|\$[A-Za-z_]+|%[^%]+%)[/\\]?", "", token).replace("\\", "/").lstrip("./")
        if token:
            referenced.update(p for p in paths if p == token or p.endswith("/" + token))
    return referenced


def static_scan(files: dict, *, food: str, commit: str | None = None, integrity: str = "unknown",
                modes: dict | None = None, skipped=(), symlinks: dict | None = None, gitlinks=()) -> dict:
    """Deterministic T0 record. Flags only; nothing here can mark a food toxic."""
    modes, symlinks = modes or {}, symlinks or {}
    paths = sorted(files)
    roles = {p: file_role(p, files[p], modes.get(p)) for p in paths}
    flags, counters, info_matches, truncated = [], {}, 0, 0
    allergens, hosts = set(), set()

    def flag(rule, severity, path, line, matched, allergen=None, meaning=""):
        nonlocal truncated
        if allergen:
            allergens.add(allergen)
        key = (rule, path)
        counters[key] = counters.get(key, 0) + 1
        if counters[key] > 3 or len(flags) >= 400:
            truncated += 1
            return
        flags.append({"id": f"{rule}:{path}:{line}", "rule": rule, "severity": severity, "path": path, "line": line,
                      "role": roles.get(path, "auto-exec"), "allergen": allergen, "meaning": meaning,
                      "match_sha256": sha256_bytes(matched.encode("utf-8"))})

    # Declared executable surfaces: hooks, MCP servers, plugin manifests, package lifecycle scripts.
    hooks, mcp, plugins, auto_exec, lifecycle = [], [], [], {}, []
    for path in paths:
        name = PurePosixPath(path).name.casefold()
        if roles[path] not in ("config", "manifest"):
            continue
        config = _json(files[path]) if name.endswith(".json") else None
        if config is None:
            continue
        is_plugin = name == "plugin.json" or name == "marketplace.json" or ".claude-plugin" in path or ".codex-plugin" in path
        if is_plugin:
            plugins.append({"path": path, "hooks": "hooks" in config, "mcp": "mcpServers" in config,
                            "declares": sorted(k for k in ("skills", "commands", "agents", "hooks", "mcpServers") if k in config)})
        if name == "hooks.json" or (name.startswith("settings") and ".claude/" in path) or (is_plugin and isinstance(config.get("hooks"), dict)):
            for event, command in _hook_commands(config):
                hooks.append({"path": path, "event": sanitize_text(event, 60), "command": command})
        servers = config.get("mcpServers") if isinstance(config.get("mcpServers"), dict) else None
        if servers is not None and (name in (".mcp.json", "mcp.json") or is_plugin or name.endswith("settings.json")):
            for server, spec in servers.items():
                spec = spec if isinstance(spec, dict) else {}
                command = " ".join(str(x) for x in [spec.get("command", ""), *(spec.get("args") or [])] if isinstance(x, (str, int)))
                mcp.append({"path": path, "name": sanitize_text(server, 64), "command": command, "remote": bool(spec.get("url"))})
        if name == "package.json" and isinstance(config.get("scripts"), dict):
            for script, command in config["scripts"].items():
                if script in ("preinstall", "install", "postinstall", "prepare", "prepublish", "preprepare", "postprepare") and isinstance(command, str):
                    lifecycle.append({"path": path, "script": script, "command": command})
    for item in hooks + mcp + lifecycle:
        for referenced in _command_paths(item["command"], paths):
            auto_exec.setdefault(referenced, item["path"])
    for item in hooks + mcp + lifecycle:
        normalized = _normalized(item["command"])
        for rule, pattern, table, allergen, meaning in _COMPILED:
            match = pattern.search(normalized)
            if match:
                flag(rule, _SEV[table]["auto-exec"], item["path"], 0, match.group(0), allergen, meaning + " (auto-run command)")
        if re.search(r"\bnpx\s+(?:-y|--yes)\s+(?!\S*@\d)\S+|\buvx\s+(?!\S*==)\S+|\bpip3?\s+install\s+(?!\S*==)[a-z]", normalized):
            flag("S-DEP", "medium", item["path"], 0, normalized[:200], "unpinned-deps", "auto-run command uses unpinned packages")
    events = sorted({h["event"] for h in hooks})
    if hooks:
        allergens.add("hooks")
        for path in sorted({h["path"] for h in hooks}):
            flag("S-HOOK", "medium", path, 0, path, "hooks", "declares auto-executing hooks")
        context = sorted(e for e in events if e.casefold() in ("sessionstart", "userpromptsubmit", "precompact", "subagentstart"))
        for event in context:
            flag("S-HOOK-CTX", "medium", next(h["path"] for h in hooks if h["event"] == event), 0, event, "writes-context",
                 f"{event} hook injects text into every session or prompt")
    if mcp:
        allergens.add("mcp")
        for server in mcp:
            flag("S-MCP", "medium", server["path"], 0, server["name"], "mcp", "declares an MCP server")
    for item in lifecycle:
        flag("S-LIFECYCLE", "medium", item["path"], 0, item["script"], "package-install", f"package {item['script']} script runs on install")

    # Line rules over text roles; docs only get the hidden-character check.
    declared, imported = [], set()
    for path in paths:
        role = "auto-exec" if path in auto_exec else roles[path]
        if role in ("binary", "asset"):
            continue
        raw = files[path].decode("utf-8", "replace")
        hidden = _HIDDEN.search(raw[1:] if raw.startswith("\ufeff") else raw)
        if hidden:
            line = raw.count("\n", 0, hidden.start() + (1 if raw.startswith("\ufeff") else 0)) + 1
            severity = {"docs": "low", "other": "medium"}.get(role, "high")
            flag("F-HID", severity, path, line, "U+%04X" % ord(hidden.group(0)), None, "hidden or bidirectional control characters")
        if role == "docs":
            continue
        if roles[path] == "manifest":
            declared.extend(_declared_deps(path, files[path]))
        if roles[path] == "executable":
            imported |= _code_imports(path, raw)
        normalized = _normalized(raw)
        hosts.update(h for h in re.findall(r"https?://([a-z0-9][a-z0-9.-]{0,200}[a-z0-9])", normalized) if "." in h)
        if not _ANY_RULE.search(normalized):
            continue
        sev_role = role if role in _SEV["critical"] else "other"
        for number, line in enumerate(normalized.split("\n"), 1):
            for rule, pattern, table, allergen, meaning in _COMPILED:
                match = pattern.search(line)
                if match:
                    flag(rule, _SEV[table][sev_role], path, number, match.group(0), allergen, meaning)

    # Import hooks, stdlib shadows and build backends would run if the tree were placed on sys.path.
    stdlib = set(getattr(sys, "stdlib_module_names", ())) - {"__future__"}
    for path in paths:
        name = PurePosixPath(path).name
        folded = name.casefold()
        if folded in _IMPORT_HOOKS or folded.endswith(".pth") or (folded.endswith(".py") and name[:-3] in stdlib):
            flag("S-SHADOW", "medium", path, 0, name, "import-hook", "would run on Python import or startup if placed on sys.path")
        elif folded == "setup.py":
            flag("S-BUILD", "medium", path, 0, name, "package-install", "build backend code runs on install")
        if folded in ROUTER_NAMES:
            flag("S-NEST", "medium", path, 0, name, "nested-instructions", "nested always-loaded instruction file")
    for path, target in sorted(symlinks.items()):
        flag("F-LINK", "low", path, 0, str(target), None, "symlink recorded, not followed")
    for path in sorted(gitlinks):
        flag("F-ARC", "low", path, 0, path, None, "submodule recorded, not fetched")
    for path in sorted(skipped):
        flag("F-PARTIAL", "medium", path, 0, path, None, "file past the archive size or count cap was not stored or scanned")

    # S-DEP / S-EXCL / S-MODEL over declared packages and code imports (text only; nothing installed).
    local = {PurePosixPath(p).stem.casefold().replace("_", "-") for p in paths if p.endswith(".py")}
    local |= {PurePosixPath(p).parts[0].casefold().replace("_", "-") for p in paths if "/" in p}
    deps = sorted({dep for dep, _spec in declared} | (imported - local))
    non_stdlib = sorted(d for d in deps if d.replace("-", "_") not in stdlib and d not in stdlib)
    exclusions = sorted({category for category, names in EXCLUSIONS.items() for name in names if name in non_stdlib})
    for category in exclusions:
        flag("S-EXCL", "medium", "(dependencies)", 0, category, "excluded:" + category,
             f"V2 exclusion: {category} (local placement only until the owner lifts it)")
    if any(d in non_stdlib for d in ("anthropic", "openai", "litellm", "@anthropic-ai/sdk", "@anthropic-ai/claude-agent-sdk", "google-generativeai")):
        allergens.add("spawns-model-calls")
    if non_stdlib:
        allergens.add("non-stdlib-deps")
    self_rewrite = any(re.search(r"self[- ]?(?:improv|rewrit|modif|evolv)", _normalized(files[p].decode("utf-8", "replace")))
                       for p in paths if roles[p] in ("instruction", "executable"))
    if self_rewrite and "background-process" in allergens:
        exclusions = sorted(set(exclusions) | {"self-rewriting-daemon"})
        flag("S-EXCL", "medium", "(behaviour)", 0, "self-rewriting-daemon", "excluded:self-rewriting-daemon",
             "V2 exclusion: background self-rewriting process")

    license_info = detect_license(files)
    if license_info["distribution"] == "unknown":
        flag("S-LIC", "medium", license_info["files"][0]["file"] if license_info["files"] else "(root)", 0,
             str(license_info["spdx"]), None, "no recognised license: redistribution not established")

    components = _split_components(files, roles, modes, flags, hooks, mcp, plugins, auto_exec, skipped)
    skills = [c["skill"] | {"component": c["id"]} for c in components if c["kind"] == "skill"]
    for component in components:
        skill = component.get("skill")
        if skill and skill["body_bytes"] > LIMITS["skill_body_bytes"]:
            flag("S-BUD", "low", skill["path"], 0, str(skill["body_bytes"]), None,
                 f"skill body {skill['body_bytes']} bytes > {LIMITS['skill_body_bytes']}")
    flag_index = {}
    for item in flags:
        flag_index.setdefault(item["path"], []).append(item["id"])
    for component in components:
        component["flag_ids"] = sorted({fid for p in component["paths"] for fid in flag_index.get(p, [])})
    digestible = any(c["kind"] in ("skill", "agent", "command", "plugin-manifest", "hook-set", "mcp-server") for c in components)
    exec_rank = {"X0": 0, "X1-inline": 1, "X1": 2, "X2": 3}
    exec_class = max((c["exec_class"] for c in components), key=exec_rank.get, default="X0")
    by_role = {}
    for path in paths:
        by_role[roles[path]] = by_role.get(roles[path], 0) + 1
    hashes = {p: sha256_bytes(files[p]) for p in paths}
    record = {
        "schema_version": SCHEMA_VERSION, "food": food, "commit": commit, "tier": "T0", "mode": "deterministic",
        "provenance": "deterministic", "level": "static-measured", "scanner_version": SCANNER_VERSION,
        "evidence_id": f"{food}@{(commit or 'unverified')[:12]}/T0/s{SCANNER_VERSION}",
        "integrity": integrity, "tree_sha256": tree_sha256(hashes),
        "counts": {"files": len(paths), "bytes": sum(len(files[p]) for p in paths), "by_role": by_role,
                   "skipped": len(list(skipped)), "symlinks": len(symlinks), "gitlinks": len(list(gitlinks))},
        "checks_run": list(SKILL_CHECKS), "license": license_info, "exec_class": exec_class,
        "allergens": sorted(allergens), "flags": flags, "flags_truncated": truncated, "info_matches": info_matches,
        "hooks": {"count": len(hooks), "events": events}, "mcp_servers": sorted({m["name"] for m in mcp}),
        "plugins": [p["path"] for p in plugins], "network_hosts": sorted(sanitize_text(h, 120) for h in hosts)[:100],
        "dependencies": {"declared": sorted({d for d, _s in declared}), "non_stdlib": non_stdlib[:200]},
        "exclusions": exclusions, "skills": skills, "components": components,
        "inedible": [] if digestible else ["no-digestible-entrypoint"],
    }
    return record


_FENCE_SHELL = re.compile(r"(?im)^\s{0,3}(?:```|~~~)\s*(?:bash|sh|shell|zsh|console|powershell|pwsh|ps1|cmd|bat)\b")
_COMMAND_WORDS = (r"curl|wget|bash|sh|zsh|fish|pwsh|powershell|iex|iwr|python3?|py|node|npx|uvx|uv|pip3?|pipx|npm|pnpm|yarn|bun|deno"
                  r"|git|gh|rm|chmod|chown|mv|cp|sudo|make|docker|podman|kubectl|cargo|go|ruby|perl|php|java|ssh|scp|nc|eval|exec"
                  r"|source|invoke-webrequest|invoke-expression|start-process|del|rmdir|claude|codex")
# An inline code span holding a command word: `curl … | sh`, `rm -rf build`, `git push --force`.
_INLINE_COMMAND = re.compile(r"`[^`\n]*(?<![\w./-])(?:" + _COMMAND_WORDS + r")(?![\w-])[^`\n]*`", re.IGNORECASE)
# Imperative prose with a quoted command: "run `…`", "執行 `…`".
_IMPERATIVE = re.compile(r"(?i)\b(?:run|execute|exec|invoke)\b[^\n`]{0,40}`[^`\n]+`|(?:執行|跑)[^\n`]{0,20}`[^`\n]+`")


def inline_exec_signals(body: str) -> list:
    """S-KIND for instruction text: why a SKILL.md body asks the agent to act (X1-inline)."""
    normalized = _normalized(body)
    signals = []
    if _FENCE_SHELL.search(body):
        signals.append("shell-fence")
    if _INLINE_COMMAND.search(normalized):
        signals.append("inline-command")
    if _IMPERATIVE.search(normalized):
        signals.append("imperative-command")
    # Any flag rule in the body (network, home directory, pipes, updates...) whatever its severity or triage.
    signals += sorted({rule for rule, pattern, *_rest in _COMPILED if pattern.search(normalized)})
    return signals


def portable_issues(data: bytes) -> list:
    """The frontmatter rules OAW's doctor applies to installed skills (scripts/validate_skills.py)."""
    try:
        import validate_skills
    except ImportError:  # the validator ships with the framework; without it the install-time lint still runs
        return []
    try:
        validate_skills._frontmatter(data.decode("utf-8-sig", "replace"))
    except ValueError as exc:
        return [sanitize_text(str(exc), 120)]
    return []


def _skill_facts(path, data, files_in_skill, modes, skipped):
    text = data.decode("utf-8", "replace")
    fields, body = parse_frontmatter(text)
    name = fields.get("name", "")
    description = fields.get("description", "")
    signals = inline_exec_signals(body)
    tools = [t.strip().split("(")[0].casefold() for t in re.split(r"[,\s]+", fields.get("allowed-tools", "")) if t.strip()]
    grants = sorted(t for t in tools if t and t not in READ_ONLY_TOOLS)
    skill_dir = str(PurePosixPath(path).parent)
    skill_dir = "" if skill_dir == "." else skill_dir
    blocked = []
    for member in files_in_skill:
        relative = member[len(skill_dir) + 1:] if skill_dir else member
        pure = PurePosixPath(relative)
        license_file = re.fullmatch(r"(?:license|licence|notice|copying)(?:\.[a-z]+)?", pure.name.casefold())
        metadata = relative.casefold() == "agents/openai.yaml"
        if ((pure.suffix.casefold() not in INSTALL_ALLOWED_SUFFIXES and not license_file and not metadata) or modes.get(member, "100644") != "100644"
                or member in skipped or pure.name.casefold() in ROUTER_NAMES
                or any(part.casefold() in (".claude", ".codex", ".agents", ".git", "hooks") for part in pure.parts[:-1])):
            blocked.append(member)
    return {"path": path, "dir": skill_dir, "name": sanitize_text(name, 64), "valid_name": bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)) and len(name) <= 64,
            "description_bytes": len(description.encode("utf-8")), "name_bytes": len(name.encode("utf-8")),
            "description_ok": bool(description.strip()) and len(description) <= 1024 and "<" not in description and ">" not in description,
            "body_bytes": len(body.encode("utf-8")), "inline_exec": bool(signals), "inline_signals": signals[:12], "tool_grants": grants,
            "portable_issues": portable_issues(data),
            "outside_allowlist": blocked[:20], "outside_allowlist_count": len(blocked)}


def _split_components(files, roles, modes, flags, hooks, mcp, plugins, auto_exec, skipped):
    """Every food is split into reviewable parts with a kind and an execution class."""
    paths = sorted(files)
    assigned, components, ids = {}, [], set()

    def add(cid, kind, name, members, exec_class, where="", **extra):
        cid = re.sub(r"[^A-Za-z0-9:._/-]+", "-", cid)[:120]
        if cid in ids and where:
            cid = f"{cid}@{slug(where, 40)}"
        base, n = cid, 2
        while cid in ids:
            cid, n = f"{base}-{n}", n + 1
        ids.add(cid)
        members = sorted(set(members))
        for member in members:
            assigned.setdefault(member, cid)
        components.append({"id": cid, "kind": kind, "name": sanitize_text(name, 80), "paths": members,
                           "file_count": len(members), "bytes": sum(len(files[m]) for m in members if m in files),
                           "exec_class": exec_class, **extra})

    for config in sorted({h["path"] for h in hooks}):
        scripts = [p for p, source in auto_exec.items() if source == config]
        add("hooks:" + config, "hook-set", config, [config, *scripts], "X2",
            events=sorted({h["event"] for h in hooks if h["path"] == config}))
    for server in mcp:
        scripts = [p for p, source in auto_exec.items() if source == server["path"] and p not in assigned]
        add("mcp:" + server["name"], "mcp-server", server["name"], [server["path"], *scripts], "X2", remote=server["remote"])
    for plugin in plugins:
        if plugin["path"] not in assigned:
            add("plugin:" + plugin["path"], "plugin-manifest", plugin["path"], [plugin["path"]], "X2" if plugin["hooks"] or plugin["mcp"] else "X0",
                declares=plugin["declares"])
    for path, source in sorted(auto_exec.items()):
        if path not in assigned:
            add("exec:auto/" + path, "executable", path, [path], "X2")
    skill_files = sorted((p for p in paths if PurePosixPath(p).name.casefold() == "skill.md"), key=lambda p: -p.count("/"))
    owner_of = {}
    for skill in skill_files:
        parent = str(PurePosixPath(skill).parent)
        prefix = "" if parent == "." else parent + "/"
        for member in paths:
            if member.startswith(prefix) and member not in owner_of and member not in assigned:
                owner_of[member] = skill
    for skill in sorted(skill_files):
        members = [m for m, owner in owner_of.items() if owner == skill]
        facts = _skill_facts(skill, files[skill], members, modes, set(skipped))
        has_code = any(roles[m] in ("executable", "manifest", "binary") for m in members)
        # Other instruction files of the skill (references it ships) count as its instructions too.
        for member in members:
            if member != skill and roles[member] in ("instruction", "docs", "other") and PurePosixPath(member).suffix.casefold() in (".md", ".txt"):
                extra = inline_exec_signals(files[member].decode("utf-8", "replace"))
                if extra:
                    facts["inline_exec"] = True
                    facts["inline_signals"] = sorted(set(facts["inline_signals"]) | set(extra))[:12]
        exec_class = "X1" if has_code else ("X1-inline" if facts["inline_exec"] or facts["tool_grants"] else "X0")
        name = facts["name"] if facts["valid_name"] else (PurePosixPath(facts["dir"]).name or "root")
        add("skill:" + slug(name), "skill", name, members, exec_class, where=facts["dir"].rsplit("/", 2)[0] if facts["dir"] else "", skill=facts)
    rest = [p for p in paths if p not in assigned]
    groups = {}
    for path in rest:
        role, pure = roles[path], PurePosixPath(path)
        if role == "instruction" and pure.name.casefold() in ROUTER_NAMES:
            add("instructions:" + path, "instruction-file", path, [path], "X1-inline")
        elif role == "instruction":
            kind = "agent" if "agents" in [p.casefold() for p in pure.parts[:-1]] else "command"
            add(f"{kind}:{slug(pure.stem)}", kind, pure.stem, [path], "X0", where=str(pure.parent.parent))
        elif role == "manifest":
            groups.setdefault(("deps", "dependency-manifest", "dependency manifests", "X1"), []).append(path)
        elif role == "executable":
            top = pure.parts[0] if len(pure.parts) > 1 else "(root)"
            groups.setdefault((f"exec:{top}", "executable", f"scripts in {top}", "X1"), []).append(path)
        elif role == "binary":
            groups.setdefault(("binaries", "binary", "binary files", "X1"), []).append(path)
        elif role == "docs":
            groups.setdefault(("docs", "docs", "documentation", "X0"), []).append(path)
        else:
            groups.setdefault(("other", "other", "config, assets and other files", "X0"), []).append(path)
    for (cid, kind, name, exec_class), members in sorted(groups.items()):
        add(cid, kind, name, members, exec_class)
    return components


# --------------------------------------------------------------------------- papers
#
# A paper is sealed as two files: the PDF of the pinned version and the metadata.json built here. The PDF is
# hashed and its first bytes compared with `%PDF-`; it is never parsed, rendered or executed. Without a model,
# v0 cannot split a paper into components, so a paper's T0 record has none; they come from the Elephant
# (planned) or an imported digestion record, and are never invented here.

PAPER_LIMITS = {"pdf_bytes": LIMITS["max_total_bytes"], "metadata_bytes": 2 * 1024 * 1024, "timeout_seconds": 60}
PAPER_FILES = ("metadata.json", "paper.pdf")
PAPER_CHECKS = ("P-META", "P-PDF", "P-LIC")
# Licenses whose text may be quoted with attribution; anything else (arXiv's non-exclusive distribution licence,
# NC/ND variants, unknown) gives the info flag P-LIC: ideas only, re-implement, never copy text.
REUSABLE_PAPER_LICENSES = ("CC-BY", "CC-BY-SA", "CC0")
PAPER_COMPONENTS_NOTE = ("component extraction needs the Elephant (planned) or an imported digestion record;"
                         " v0 extracts none from a paper and invents none")
PAPER_COMPONENTS_NOTE_ZH = "論文的成分要由 Elephant 拆（規劃中），或匯入已有的消化紀錄；v0 不會自己拆，也不會編造成分"


def _local(tag) -> str:
    return str(tag).rsplit("}", 1)[-1]


def parse_arxiv_raw(data: bytes) -> dict:
    """Title, authors, abstract, license and versions from an OAI-PMH GetRecord response in arXivRaw format.

    A document type declaration is refused before parsing, so no entity can expand. An OAI-PMH error
    (for example idDoesNotExist) raises ValueError with "arXiv has no record".
    """
    import xml.etree.ElementTree as ElementTree
    if len(data) > PAPER_LIMITS["metadata_bytes"]:
        raise ValueError("response exceeds the metadata limit")
    if re.search(rb"<!(?:DOCTYPE|ENTITY)", data, re.IGNORECASE):
        raise ValueError("document type declarations are refused")
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError(f"not XML: {exc}") from exc
    error = next((e for e in root.iter() if _local(e.tag) == "error"), None)
    if error is not None:
        raise ValueError(f"arXiv has no record ({sanitize_text(error.get('code'), 40)}): {sanitize_text(error.text, 120)}")
    raw = next((e for e in root.iter() if _local(e.tag) == "arXivRaw"), None)
    if raw is None:
        raise ValueError("no arXivRaw record in the response")

    def field(name, limit=300):
        node = next((e for e in raw if _local(e.tag) == name), None)
        return sanitize_text("".join(node.itertext()), limit) if node is not None else ""
    versions = []
    for node in raw:
        if _local(node.tag) != "version" or not re.fullmatch(r"v[1-9]\d{0,3}", str(node.get("version") or "")):
            continue
        date_node = next((e for e in node if _local(e.tag) == "date"), None)
        versions.append({"version": node.get("version"), "date": _rfc2822_date(date_node.text if date_node is not None else ""),
                         "size": sanitize_text(next((e.text for e in node if _local(e.tag) == "size"), ""), 20)})
    versions.sort(key=lambda v: int(v["version"][1:]))
    abstract_node = next((e for e in raw if _local(e.tag) == "abstract"), None)
    abstract = re.sub(r"\s+", " ", "".join(abstract_node.itertext())).strip() if abstract_node is not None else ""
    authors = [sanitize_text(a, 120) for a in re.split(r",\s*|\s+and\s+", field("authors", 20000)) if a.strip()]
    try:
        arxiv_id, _version = arxiv_identity(field("id", 40))
    except SourceError as exc:
        raise ValueError(str(exc)) from exc
    return {"arxiv_id": arxiv_id, "title": field("title"), "authors": authors[:200], "abstract": abstract[:20000],
            "license_url": field("license", 200) or None, "categories": field("categories", 200).split()[:20],
            "versions": versions}


def _rfc2822_date(text) -> str:
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(str(text).strip()).date().isoformat()
    except (TypeError, ValueError, IndexError):
        return sanitize_text(text, 40)


def paper_license(url) -> dict:
    """The license a paper was released under, from its license URL, and what OAW may reuse."""
    text = str(url or "").strip().casefold().replace("https://", "http://")
    match = re.search(r"creativecommons\.org/licenses/([a-z-]+)/(\d\.\d)", text)
    if match:
        spdx = f"CC-{match.group(1).upper()}-{match.group(2)}"
    elif re.search(r"creativecommons\.org/publicdomain/zero/1\.0", text):
        spdx = "CC0-1.0"
    elif "arxiv.org/licenses/nonexclusive-distrib/" in text:
        spdx = "LicenseRef-arXiv-nonexclusive-distrib-1.0"
    else:
        spdx = "unknown"
    reusable = spdx != "unknown" and spdx.rsplit("-", 1)[0] in REUSABLE_PAPER_LICENSES
    note = (("quoted text may be reused with attribution", "引用原文要附出處（作者、標題、arXiv 編號、版本、授權）") if reusable
            else ("ideas only: re-implement, do not copy text", "只取想法：重新實作，不複製原文"))
    return {"spdx": spdx, "url": sanitize_text(url, 200) or None, "reuse": "quote-with-attribution" if reusable else "ideas-only",
            "reuse_note": note[0], "reuse_note_zh": note[1], "distribution": "redistributable" if reusable else "local-only",
            "files": []}


def paper_metadata(snapshot: dict) -> bytes:
    """The metadata.json sealed beside the PDF: deterministic (no timestamps), with the sha256 of each input."""
    meta = snapshot.get("metadata") or {}
    pdf = snapshot["pdf"]
    doc = {"schema_version": 1, "kind": "oaw-paper-metadata", "source": snapshot.get("source", "local"),
           "arxiv_id": meta.get("arxiv_id"), "version": snapshot.get("version"), "versions": meta.get("versions", []),
           "title": meta.get("title") or None, "authors": meta.get("authors", []), "abstract": meta.get("abstract", ""),
           "license_url": meta.get("license_url"), "categories": meta.get("categories", []),
           "file_name": sanitize_text(snapshot.get("file_name"), 120) or None,
           "pdf": {"name": "paper.pdf", "sha256": sha256_bytes(pdf), "bytes": len(pdf)},
           "metadata_response_sha256": snapshot.get("metadata_sha256")}
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def paper_scan(files: dict, *, food: str, integrity: str = "sha256-recorded") -> dict:
    """A paper's deterministic T0 record from its sealed files: metadata, PDF hash and the license rule.

    No hook, MCP or script check applies to a paper, and nothing here can mark it toxic. The license rule only
    adds an info flag (P-LIC, never open for triage). Components stay empty: see PAPER_COMPONENTS_NOTE.
    """
    pdf, meta_bytes = files.get("paper.pdf", b""), files.get("metadata.json", b"")
    meta = _json(meta_bytes) or {}
    hashes = {p: sha256_bytes(files[p]) for p in sorted(files)}
    license_info = paper_license(meta.get("license_url"))
    version = meta.get("version") if re.fullmatch(r"v[1-9]\d{0,3}", str(meta.get("version") or "")) else None
    pin = f"{version or 'local'}-{hashes.get('paper.pdf', '')[:12]}"
    flags = []
    if license_info["reuse"] == "ideas-only":
        flags.append({"id": "P-LIC:metadata.json:0", "rule": "P-LIC", "severity": "info", "path": "metadata.json", "line": 0,
                      "role": "docs", "allergen": None, "meaning": license_info["reuse_note"] + f" ({license_info['spdx']})",
                      "match_sha256": sha256_bytes(str(license_info["url"] or "").encode("utf-8"))})
    authors = [sanitize_text(a, 120) for a in meta.get("authors", []) if isinstance(a, str)] if isinstance(meta.get("authors"), list) else []
    abstract = meta.get("abstract") if isinstance(meta.get("abstract"), str) else ""
    versions = [{"version": v.get("version"), "date": sanitize_text(v.get("date"), 40)} for v in meta.get("versions", [])
                if isinstance(v, dict) and re.fullmatch(r"v[1-9]\d{0,3}", str(v.get("version") or ""))][:50]
    paper = {"source": "arxiv" if meta.get("source") == "arxiv" else "local", "arxiv_id": sanitize_text(meta.get("arxiv_id"), 40) or None,
             "version": version, "version_date": next((v["date"] for v in versions if v["version"] == version), None),
             "versions": versions, "title": sanitize_text(meta.get("title"), 300) or None,
             "authors": authors[:20], "authors_total": len(authors), "abstract_chars": len(abstract),
             "categories": [sanitize_text(c, 40) for c in meta.get("categories", []) if isinstance(c, str)][:20],
             "license": license_info["spdx"], "license_url": license_info["url"], "reuse": license_info["reuse"],
             "reuse_note": license_info["reuse_note"], "reuse_note_zh": license_info["reuse_note_zh"],
             "pdf_sha256": hashes.get("paper.pdf"), "pdf_bytes": len(pdf), "metadata_sha256": hashes.get("metadata.json"),
             "is_pdf": pdf.startswith(b"%PDF-"), "parsed": False, "executed": False}
    inedible = [] if paper["is_pdf"] and meta else ["not-a-pdf" if not paper["is_pdf"] else "no-metadata"]
    return {
        "schema_version": SCHEMA_VERSION, "food": food, "food_kind": "paper", "commit": None, "version": version, "tier": "T0",
        "mode": "deterministic", "provenance": "deterministic", "level": "static-measured", "scanner_version": SCANNER_VERSION,
        "evidence_id": f"{food}@{pin}/T0/s{SCANNER_VERSION}", "integrity": integrity, "tree_sha256": tree_sha256(hashes),
        "counts": {"files": len(files), "bytes": sum(len(v) for v in files.values()), "by_role": {"paper": 1, "metadata": 1},
                   "skipped": 0, "symlinks": 0, "gitlinks": 0},
        "checks_run": list(PAPER_CHECKS), "license": license_info, "exec_class": None, "allergens": [], "flags": flags,
        "flags_truncated": 0, "info_matches": 0, "hooks": {"count": 0, "events": []}, "mcp_servers": [], "plugins": [],
        "network_hosts": [], "dependencies": {"declared": [], "non_stdlib": []}, "exclusions": [], "skills": [],
        "components": [], "components_note": PAPER_COMPONENTS_NOTE, "paper": paper, "inedible": inedible,
    }


# --------------------------------------------------------------------------- derive

def evidence_class(record) -> str:
    """static, live, historical, tasting, absorption or ignored. Imported reports are always historical.

    An agent tasting and a D21 absorption (D28) are their own classes: derive() never counts them, so they
    cannot raise a headline or lift a copy-absorb hold; food_records() checks them again for the view.
    """
    if isinstance(record, dict) and record.get("schema") == TASTING_SCHEMA and record.get("provenance") == "agent-tasting":
        return "tasting"
    if isinstance(record, dict) and record.get("schema") == ABSORPTION_SCHEMA and record.get("provenance") == "agent-absorption":
        return "absorption"
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        return "ignored"
    if record.get("provenance") == "imported-report" or record.get("mode") == "historical-prior" or record.get("level") == "historical-prior":
        return "historical"
    if (record.get("provenance") == "deterministic" and record.get("mode") == "deterministic"
            and record.get("tier") == "T0" and record.get("level") == "static-measured"):
        return "static"
    if (record.get("provenance") in LIVE_PROVENANCE and record.get("mode") == "live" and record.get("level") == "measured"
            and _HEX64.fullmatch(str(record.get("bundle_sha256") or "")) and isinstance(record.get("consent_id"), str)
            and record["consent_id"]):
        return "live"
    return "ignored"


def decisions_for(decisions, fid: str) -> list:
    """One food's decisions after its latest `forget` record: a forgotten food starts over if fed again."""
    mine = [d for d in decisions or () if isinstance(d, dict) and d.get("food") == fid]
    cut = max((index for index, d in enumerate(mine) if d.get("kind") == "forget"), default=-1)
    return mine[cut + 1:]


def _valid_decision(decision) -> bool:
    if not isinstance(decision, dict) or decision.get("kind") not in DECISION_KINDS:
        return False
    if decision["kind"] == "triage":
        return decision.get("outcome") in TRIAGE_OUTCOMES and isinstance(decision.get("flag"), str)
    return True


def _verdict(code, reasons, **extra):
    symbol, ascii_symbol, label, label_zh = VERDICTS[code]
    return {"headline": code, "symbol": symbol, "ascii": ascii_symbol, "label": label, "label_zh": label_zh,
            "reasons": list(reasons), **extra}


MISSING_TESTS = {
    "tx": ("sandbox trial in a disposable environment (TX) - paid, not enabled in v0", "在可拋棄環境（TX）試跑：付費，v0 尚未開放"),
    "smaller-skill": ("re-implement a smaller OAW skill, then T0 again", "重新實作成較小的 OAW skill，再跑一次免費檢查"),
    "fix-structure": ("fix structure, then T0 again", "修正結構後，再跑一次免費檢查"),
    "fix-portable": ("fix structure (OAW portable frontmatter), then T0 again", "改成 OAW 可攜的 frontmatter，再跑一次免費檢查"),
    "without-files": ("re-implement without those files", "不帶那些檔案重新實作"),
    "license-check": ("owner license check", "由你確認授權"),
    "triage": ("owner triage of the flags", "由你分流這些旗標"),
    "reimplement-ab": ("behavior A/B (paid), after re-implementation", "重新實作後做行為 A/B（付費）"),
    "method-backlog": ("elephant proposal (method backlog)", "Elephant 提案（方法待辦）"),
    "elephant": ("elephant proposal", "Elephant 提案"),
    "food-triage": ("owner triage", "由你分流"),
    "ab": ("behavior A/B (paid): model-facing text is held behind an A/B (D17)", "行為 A/B（付費）：模型面向的文字要過 A/B 才能吸收（D17）"),
    "retaste": ("taste again with the current free rules", "用目前的規則再試吃一次（免費）"),
}


def _signal_text(signals) -> tuple:
    names = {"shell-fence": ("a shell code block", "shell 程式碼區塊"), "inline-command": ("an inline command", "行內指令"),
             "imperative-command": ("a 'run …' instruction", "「執行 …」的指示")}
    english = [names.get(s, (s, s))[0] for s in signals[:3]]
    chinese = [names.get(s, (s, s))[1] for s in signals[:3]]
    return ", ".join(english), "、".join(chinese)


def propose_component(component: dict, open_flags: dict, license_info: dict, ab_passed: bool = False) -> dict:
    """Proposed disposition and the reason; executable or flagged parts never default to absorb.

    D17: a model-facing line (a skill's text) is held behind a behavior A/B, so an X0 skill becomes
    absorbable only with `ab_passed` (a consented live A/B with a gain and a parity floor covering it).
    A high-severity flag holds its part until the owner triages it. A rule excrete (package manifests,
    a second instruction file, binaries) is final: it applies an OAW policy, not a guess.
    Every reason has a stable `reason_code`, the English `reason` and the
    Traditional Chinese `reason_zh`; `missing_test` likewise has `missing_zh`.
    """
    own = [open_flags[f] for f in component.get("flag_ids", []) if f in open_flags]
    high = [f for f in own if f["severity"] == "high"]
    medium = [f for f in own if f["severity"] == "medium"]
    kind = component["kind"]
    kinds_zh = {"hook-set": "hooks", "mcp-server": "MCP server", "agent": "agent", "command": "指令"}

    def result(disposition, code, reason, reason_zh, missing="", owner_confirms=False, installable=False):
        missing_en, missing_zh = MISSING_TESTS[missing] if missing else ("", "")
        return {"disposition": disposition, "reason_code": code, "reason": reason, "reason_zh": reason_zh,
                "missing_code": missing, "missing_test": missing_en, "missing_zh": missing_zh,
                "owner_confirms": owner_confirms, "installable": installable}

    if high:
        refs = ", ".join(f"{f['rule']} {f['path']}:{f['line']}" for f in high[:3])
        return result("hold", "high-flags", f"high-severity static flag(s): {refs}; held until the owner triages them (static rules never mark toxic)",
                      f"高嚴重度靜態旗標：{refs}；你分流之前暫留（靜態規則只會舉旗，不會判有毒）", "triage")
    if kind == "skill":
        skill = component["skill"]
        if skill["body_bytes"] > LIMITS["skill_body_bytes"]:
            return result("hold", "skill-too-large", f"inedible as shipped: body {skill['body_bytes']} bytes > {LIMITS['skill_body_bytes']} (not harmful)",
                          f"照原樣不能吃：本文 {skill['body_bytes']} bytes 超過 {LIMITS['skill_body_bytes']}（不是有害）", "smaller-skill")
        if not skill["valid_name"] or not skill.get("description_ok"):
            return result("hold", "skill-structure", "SKILL.md lacks a valid lowercase name or a portable description",
                          "SKILL.md 缺少有效的小寫名稱或可攜的描述", "fix-structure")
        if skill.get("portable_issues"):
            issue = skill["portable_issues"][0]
            return result("hold", "skill-portable", f"SKILL.md fails OAW's portable skill lint: {issue}",
                          f"SKILL.md 不符合 OAW 的可攜 skill 格式：{issue}", "fix-portable")
        if component["exec_class"] != "X0":
            if component["exec_class"] == "X1":
                return result("hold", "exec-x1", "X1: bundles scripts; never run on this machine",
                              "X1：附帶腳本；永遠不在這台電腦上執行", "tx")
            english, chinese = _signal_text(skill.get("inline_signals") or (["tool-grants"] if skill.get("tool_grants") else []))
            return result("hold", "exec-x1-inline", f"X1-inline: instructs shell, network or tool actions ({english}); never run on this machine",
                          f"X1-inline：指示 agent 執行 shell／網路／工具動作（{chinese}）；永遠不在這台電腦上執行", "tx")
        if skill["outside_allowlist_count"]:
            count = skill["outside_allowlist_count"]
            return result("hold", "outside-allowlist", f"{count} file(s) outside the install allowlist (.md/.txt, mode 644, no nested instructions)",
                          f"{count} 個檔案不在安裝允許清單內（只收 .md／.txt、權限 644、不含巢狀指示檔）", "without-files")
        if license_info.get("distribution") == "unknown":
            return result("hold", "license-unknown", "license unknown: copying is not established", "授權不明：不能確定可以複製", "license-check")
        if medium:
            refs = ", ".join(f"{f['rule']} {f['path']}:{f['line']}" for f in medium[:3])
            return result("hold", "open-flags", f"open flag(s): {refs}", f"未分流的旗標：{refs}", "triage")
        spdx = str(license_info.get("spdx"))
        if not ab_passed:
            return result("hold", "x0-text-ab", f"X0 skill text passed the static checks (no shell, network or tool instructions; no open flags;"
                          f" license {spdx}); model-facing text is held behind a behavior A/B (D17)",
                          f"X0 skill 文字通過靜態檢查（沒有 shell／網路／工具指示、沒有未分流的旗標、授權 {spdx}）；"
                          "模型面向的文字要過行為 A/B 才能吸收（D17）", "ab")
        return result("absorb", "x0-skill", f"X0 skill text: static checks passed (license {spdx}) and a consented behavior A/B with a"
                      " parity floor covers it (D17); copied unchanged with its license and an attribution note",
                      f"X0 skill 文字：靜態檢查通過（授權 {spdx}），而且有經同意的行為 A/B（含齊平底線）涵蓋它（D17）；"
                      "照原樣複製，附上授權和出處說明", installable=True)
    if kind in ("hook-set", "mcp-server"):
        return result("hold", "auto-exec", f"{kind} auto-executes (X2); OAW never installs hooks or MCP servers",
                      f"{kinds_zh[kind]} 會自動執行（X2）；OAW 永遠不代裝 hooks 或 MCP server", "tx")
    if kind == "plugin-manifest":
        return result("hold", "plugin", "host plugin manifest; plugins are installed by the owner through the host, never by OAW",
                      "host plugin 清單：plugin 由你透過 host 安裝，OAW 不代裝", "tx")
    if kind == "executable":
        return result("hold", "executable", "executable code; never run on this machine", "可執行的程式碼；永遠不在這台電腦上執行", "tx")
    if kind == "dependency-manifest":
        return result("excrete", "deps", "package manifests conflict with OAW's stdlib-only runtime; nothing is installed (rule excrete, final)",
                      "套件清單和 OAW 只用標準函式庫的原則衝突；不會安裝任何東西（依規則排掉，是最終的）")
    if kind == "instruction-file":
        return result("excrete", "instruction-file", "a second always-loaded instruction file conflicts with OAW's single AGENTS.md policy"
                      " (rule excrete, final)", "第二份常駐指示檔和 OAW 只用一份 AGENTS.md 的原則衝突（依規則排掉，是最終的）")
    if kind in ("agent", "command"):
        return result("hold", "prompt", f"{kind} prompt, not a native skill; needs re-implementation as an OAW skill",
                      f"{kinds_zh[kind]}提示詞，不是原生 skill：要重新實作成 OAW skill", "reimplement-ab")
    if kind == "binary":
        return result("excrete", "binary", "binary files cannot be reviewed as text (rule excrete, final)",
                      "二進位檔沒辦法當文字審查（依規則排掉，是最終的）")
    if kind == "docs":
        return result("hold", "docs", "reference material; never installed", "參考資料；永遠不會安裝", "method-backlog")
    return result("hold", "other", "not digestible as shipped", "照原樣沒辦法消化", "elephant")


def derive(evidence, decisions=(), *, tier: str = "local") -> dict:
    """Food headline and per-component dispositions from evidence and owner decisions only.

    Imported reports and records without a consented live bundle are ignored, so
    they can never raise a verdict. Owner decisions can confirm toxicity,
    excrete parts or record absorption; they cannot raise a disposition.
    """
    static, live = [], []
    for record in evidence or ():
        kind = evidence_class(record)
        if kind == "static":
            static.append(record)
        elif kind == "live":
            live.append(record)
    decisions = [d for d in (decisions or ()) if _valid_decision(d)]
    triage = {d["flag"]: d["outcome"] for d in decisions if d["kind"] == "triage"}
    toxic_refs = sorted(flag for flag, outcome in triage.items() if outcome == "confirm-toxic")
    blocked = [d for d in decisions if d["kind"] in ("block", "reject")]
    base = {"tier": tier, "verdict_rules_version": VERDICT_RULES_VERSION, "chips": [], "badges": [], "stale": False}
    if not static:
        verdict = (_verdict("toxic", ["owner-confirmed: " + r for r in toxic_refs]) if toxic_refs
                   else _verdict("untested", ["no static record (taste not run)"]))
        verdict["reasons_zh"] = [reason_zh(r) for r in verdict["reasons"]]
        return {**base, **verdict, "level": "not-measured", "safety": "toxic" if toxic_refs else "unknown",
                "exec_class": None, "allergens": [], "flags": {"total": 0, "open": 0, "open_high": 0, "triaged": 0, "info": 0},
                "food_kind": None, "components": [], "inputs": []}
    s = max(static, key=lambda r: (int(r.get("scanner_version") or 0), str(r.get("recorded_at") or ""), str(r.get("evidence_id"))))
    chips = []
    stale = int(s.get("scanner_version") or 0) < SCANNER_VERSION
    if stale:
        chips.append("rules-updated-free-T0-pending")
    all_flags = [f for f in s.get("flags", []) if isinstance(f, dict) and isinstance(f.get("id"), str)]
    # An info flag (a paper's P-LIC "ideas only") informs; it never waits for triage or holds anything.
    open_flags = {f["id"]: f for f in all_flags if f.get("severity") != "info" and triage.get(f["id"]) not in ("benign", "allergen")}
    open_high = [f for f in open_flags.values() if f.get("severity") == "high"]
    inputs = [s.get("evidence_id")] + [r.get("evidence_id") for r in live]
    if toxic_refs:
        verdict = _verdict("toxic", ["owner-confirmed: " + r for r in toxic_refs])
        safety = "toxic"
    elif s.get("inedible"):
        verdict = _verdict("inedible", list(s["inedible"]), note="OAW cannot digest it; not a safety or quality verdict")
        safety = "flagged" if open_flags else "no-toxic-signal"
    elif open_high or blocked:
        reasons = [f"{len(open_high)} high-severity flag(s) not triaged"] if open_high else []
        reasons += [f"owner {d['kind']}: {sanitize_text(d.get('reason', ''), 80)}" for d in blocked]
        verdict, safety = _verdict("risky", reasons), "flagged"
    elif live:
        verdict, safety = _measured_verdict(live), "flagged" if open_flags else "no-toxic-signal"
    else:
        if not open_flags:
            chips.append("free-checks-passed")
        else:
            chips.append(f"open-flags:{len(open_flags)}")
        verdict = _verdict("untested", ["no measured evidence (paid tests not run)"])
        safety = "flagged" if open_flags else "no-toxic-signal"
    components = []
    component_decisions = {}
    for d in decisions:
        for cid in d.get("components") or ([d["component"]] if isinstance(d.get("component"), str) else []):
            component_decisions.setdefault(cid, []).append(d)
    # D17: a consented live A/B with a gain covers only the components it names, and only a nutritious food passes.
    ab_covered = {cid for r in live if r.get("result") == "gain" for cid in (r.get("components") or []) if isinstance(cid, str)}
    ab_ok = verdict["headline"] == "nutritious"
    tasted_at = str(s.get("recorded_at") or "")
    for component in s.get("components", []):
        proposal = propose_component(component, open_flags, s.get("license") or {}, ab_passed=ab_ok and component["id"] in ab_covered)
        confirmed = sorted(set(component.get("flag_ids", [])) & set(toxic_refs))
        if confirmed:
            refs = ", ".join(confirmed[:3])
            proposal.update(disposition="excrete", reason_code="owner-toxic", reason=f"owner-confirmed toxic: {refs}",
                            reason_zh=f"你確認有毒：{refs}", owner_confirms=False, installable=False,
                            missing_code="", missing_test="", missing_zh="")
        elif verdict["headline"] in ("toxic", "risky", "inedible") and proposal["reason_code"] in ("x0-skill", "x0-text-ab"):
            proposal.update(disposition="hold", reason_code="inherits-food", reason=f"food is {verdict['headline']}; parts inherit it until resolved",
                            reason_zh=f"整樣食物是「{VERDICTS[verdict['headline']][3]}」；解決之前，成分一律跟著暫留",
                            missing_code="food-triage", missing_test=MISSING_TESTS["food-triage"][0],
                            missing_zh=MISSING_TESTS["food-triage"][1], installable=False)
        elif stale and proposal["reason_code"] in ("x0-skill", "x0-text-ab"):
            # A record from older rules cannot prove what the current rules would find.
            proposal.update(disposition="hold", reason_code="rules-updated", reason="the scan rules changed since this taste; taste again (free)",
                            reason_zh="試吃之後掃描規則更新了：再試吃一次（免費）", missing_code="retaste",
                            missing_test=MISSING_TESTS["retaste"][0], missing_zh=MISSING_TESTS["retaste"][1], installable=False)
        decided, removed_at = None, None
        for d in component_decisions.get(component["id"], []):
            if d["kind"] == "excrete":
                owner_reason = sanitize_text(d.get("reason", ""), 120)
                proposal.update(disposition="excrete", reason_code="owner-excreted", reason="owner excreted: " + owner_reason,
                                reason_zh="你排掉的：" + owner_reason, owner_confirms=False, installable=False)
                decided = "excreted"
            elif d["kind"] == "absorb" and proposal["disposition"] == "absorb" and decided != "excreted":
                decided, removed_at = "absorbed", None
            elif d["kind"] == "remove" and decided == "absorbed":
                decided, removed_at = "removed", str(d.get("at") or "")
        # D6: re-adding a removed part needs a taste recorded after the removal (free), never the old one.
        retested = decided == "removed" and bool(removed_at) and tasted_at > removed_at
        colour, label_zh = DISPOSITIONS[proposal["disposition"]]
        components.append({"id": component["id"], "kind": component["kind"], "name": component.get("name"),
                           "file_count": component.get("file_count"), "bytes": component.get("bytes"),
                           "exec_class": component.get("exec_class"), **proposal, "colour": colour, "label_zh": label_zh,
                           "level": "measured" if proposal["reason_code"] == "x0-skill" else "static-measured",
                           "decision": decided, "retested_after_remove": retested,
                           "open_flags": [f for f in component.get("flag_ids", []) if f in open_flags]})
    verdict["reasons_zh"] = [reason_zh(r) for r in verdict["reasons"]]
    info = sum(1 for f in all_flags if f.get("severity") == "info")
    return {**base, **verdict, "chips": chips + verdict.pop("chips", []), "stale": stale,
            "level": "measured" if live and verdict["headline"] not in ("toxic", "risky", "inedible") else "static-measured",
            "safety": safety, "exec_class": s.get("exec_class"), "allergens": list(s.get("allergens", [])),
            "flags": {"total": len(all_flags), "open": len(open_flags), "open_high": len(open_high),
                      "triaged": len(all_flags) - len(open_flags) - info, "info": info},
            "food_kind": "paper" if s.get("food_kind") == "paper" else "repo", "components": components, "inputs": inputs}


def _measured_verdict(live) -> dict:
    """Minimal rules for consented live evidence (no v0 runner produces it yet)."""
    results = [r.get("result") for r in live]
    if any(r.get("result") == "regressed" and (r.get("deterministic") or r.get("confirmed")) for r in live):
        return _verdict("regressed", ["measured regression"])
    if "regressed" in results:
        return _verdict("incomplete", ["unconfirmed-negative: one cohort; not absorbable, not proven harmful"])
    if "incomplete" in results or any(r not in ("gain", "no-gain") for r in results):
        return _verdict("incomplete", ["measured evidence is incomplete"])
    if all(r == "no-gain" for r in results):
        return _verdict("no-gain", ["no gain observed under this specification"])
    gain = [r for r in live if r.get("result") == "gain"]
    if any(r.get("integration") == "diarrhea" and r.get("confirmed") for r in gain):
        return _verdict("diarrhea", ["harms the current recipe"])
    if not any(r.get("integration") == "clear" for r in gain):
        return _verdict("incomplete", ["integration-not-complete"])
    parity = {r.get("parity") for r in gain}
    if not parity & {"parity", "evolved"}:
        return _verdict("incomplete", ["parity-floor-not-run"])
    return _verdict("nutritious", ["measured gain with parity floor"], badges=["evolved"] if "evolved" in parity else [])


# --------------------------------------------------------------------------- builds and effect

def build_hash(file_hashes: dict) -> str:
    return tree_sha256(file_hashes)


def build_name(number: int, file_hashes: dict, release: str = RELEASE) -> str:
    """SemVer 2.0 build metadata: 2.0.0+build.N.<hash7>."""
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ValueError("Build numbers start at 1.")
    name = f"{release}+build.{number}.{build_hash(file_hashes)[:7]}"
    parse_build_name(name)
    return name


def parse_build_name(name: str) -> dict:
    match = re.fullmatch(r"((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))\+build\.((?:0|[1-9]\d*))\.([0-9a-f]{7})", str(name))
    if not match:
        raise ValueError(f"Not a SemVer 2.0 OAW build name: {sanitize_text(name, 80)!r}")
    return {"release": match.group(1), "number": int(match.group(2)), "hash7": match.group(3)}


_SKILL_PATH = re.compile(r"\.(agents|claude)/skills/([^/]+)/SKILL\.md")
_HOST_SETTING_PATHS = (".claude/settings.json", ".claude/settings.local.json", ".codex/config.toml", ".codex/hooks.json", ".mcp.json")


def install_inventory(files: dict) -> dict:
    """Static inventory of an OAW install layer given {relative path: bytes}."""
    skills, startup, hooks, deps = {}, {"codex": 0, "claude": 0}, 0, set()
    local_modules = {PurePosixPath(p).stem.casefold().replace("_", "-") for p in files if p.endswith(".py")}
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    agents_md = len(files.get("AGENTS.md", b""))
    claude_md = files.get("CLAUDE.md", b"")
    startup["codex"] += agents_md
    startup["claude"] += len(claude_md) + (agents_md if re.search(rb"(?m)(?:^|\s)@(?:\./)?AGENTS\.md", claude_md) else 0)
    for path, data in sorted(files.items()):
        match = _SKILL_PATH.fullmatch(path)
        if match:
            host = "codex" if match.group(1) == "agents" else "claude"
            fields, _body = parse_frontmatter(data.decode("utf-8", "replace"))
            meta = len(fields.get("name", "").encode()) + len(fields.get("description", "").encode())
            entry = skills.setdefault(match.group(2), {"hosts": [], "metadata_bytes": meta})
            entry["hosts"].append(host)
            startup[host] += meta
        elif re.fullmatch(r"\.claude/agents/[^/]+\.md", path):
            fields, _body = parse_frontmatter(data.decode("utf-8", "replace"))
            startup["claude"] += len(fields.get("name", "").encode()) + len(fields.get("description", "").encode())
        name = PurePosixPath(path).name.casefold()
        if name.endswith(".json") and (name == "hooks.json" or path in _HOST_SETTING_PATHS):
            config = _json(data)
            if config:
                hooks += sum(1 for _ in _hook_commands(config))
        if path.endswith(".py"):
            deps |= {m for m in _code_imports(path, data.decode("utf-8", "replace"))
                     if m.replace("-", "_") not in stdlib and m not in local_modules and m != "__future__"}
        elif PurePosixPath(path).name.casefold() in ("package.json", "requirements.txt", "pyproject.toml"):
            deps |= {d for d, _spec in _declared_deps(path, data)}
    return {"skills": {k: {"hosts": sorted(v["hosts"]), "metadata_bytes": v["metadata_bytes"]} for k, v in sorted(skills.items())},
            "files": len(files), "bytes": sum(len(v) for v in files.values()),
            "startup_bytes": {"AGENTS.md": agents_md, "CLAUDE.md": len(claude_md), "by_host": startup},
            "hooks": hooks, "non_stdlib_deps": sorted(deps),
            "host_settings_writes": sorted(p for p in files if p in _HOST_SETTING_PATHS)}


def effect_vs_default(current: dict, default: dict, measured=(), hosts=None) -> dict:
    """Effect of this build versus the default release. Quality is not measured without live evidence.

    With the install's `hosts`, a skill present on only some of them is listed in `skills.only_on`.
    """
    lines = []

    def line(metric, now, base, level="static-measured", note=""):
        delta = now - base if isinstance(now, int) and isinstance(base, int) else None
        lines.append({"metric": metric, "current": now, "default": base, "delta": delta, "level": level, "note": note})

    added = sorted(set(current["skills"]) - set(default["skills"]))
    removed = sorted(set(default["skills"]) - set(current["skills"]))
    line("skills", len(current["skills"]), len(default["skills"]), note=f"added {len(added)}, removed {len(removed)}")
    line("files", current["files"], default["files"])
    line("bytes", current["bytes"], default["bytes"])
    for host in ("codex", "claude"):
        line(f"startup-loaded text bytes ({host})", current["startup_bytes"]["by_host"][host], default["startup_bytes"]["by_host"][host],
             note="AGENTS.md/CLAUDE.md plus every SKILL.md name+description; bytes/4 is only a token estimate")
    line("hooks", current["hooks"], default["hooks"])
    line("non-stdlib dependencies", len(current["non_stdlib_deps"]), len(default["non_stdlib_deps"]),
         note=", ".join(current["non_stdlib_deps"]) or "none")
    line("host settings writes", len(current["host_settings_writes"]), len(default["host_settings_writes"]),
         note=", ".join(current["host_settings_writes"]) or "none")
    live = [r for r in measured or () if evidence_class(r) == "live"]
    if live:
        verdict = _measured_verdict(live)
        quality = {"metric": "quality", "value": verdict["label"], "level": "measured",
                   "note": "enhanced" if verdict["headline"] == "nutritious" else "no improvement claimed"}
    else:
        quality = {"metric": "quality", "value": "not measured", "level": "not-measured",
                   "note": "no consented live comparison; never shown as enhanced"}
    quality.update(current=None, default=None, delta=None)
    lines.append(quality)
    only_on = {}
    if hosts:
        for name, info in current["skills"].items():
            present = sorted(set(info.get("hosts", [])) & set(hosts))
            if present != sorted(set(hosts)):
                only_on[name] = present
    return {"release": RELEASE, "skills": {"added": added, "removed": removed,
                                           "same": sorted(set(current["skills"]) & set(default["skills"])), "only_on": only_on},
            "lines": lines, "quality": quality}


# --------------------------------------------------------------------------- policy and plans

def validate_policy(per_food_tokens, weekly_tokens, sandbox) -> dict:
    if not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10**10 for v in (per_food_tokens, weekly_tokens)):
        raise ValueError("Token caps must be whole numbers between 0 and 10^10.")
    if weekly_tokens < per_food_tokens:
        raise ValueError("The weekly cap must be at least the per-food cap.")
    conditions = sorted(set(sandbox))
    unknown = [c for c in conditions if c not in SANDBOX_CONDITIONS]
    if unknown or not conditions:
        raise ValueError("Sandbox conditions must be a nonempty subset of: " + ", ".join(SANDBOX_CONDITIONS))
    return {"schema_version": SCHEMA_VERSION, "per_food_token_cap": per_food_tokens, "weekly_token_cap": weekly_tokens,
            "sandbox": conditions, "paid_runs_enabled": False}


def _tokens(runs):
    return {"runs": runs, "min": runs * TOKENS_PER_RUN[0], "max": runs * TOKENS_PER_RUN[1], "label": TOKEN_LABEL, "label_zh": TOKEN_LABEL_ZH}


# Traditional Chinese for every plan step: id -> (name, can prove, cannot prove).
PLAN_STEPS_ZH = {
    "T0": ("免費靜態檢查", ["檔案清單、授權、宣告的 hooks／MCP／腳本、旗標"], ["行為、品質、執行時的安全"]),
    "T1": ("離線整合（名稱衝突、doctor／migrate 往返）", ["安裝相容性"], ["品質"]),
    "T2a": ("人工分流高嚴重度旗標（可選：只有要照原樣複製帶旗標的成分或確認有毒時才需要，D28）", ["每個旗標是良性、過敏原，還是有毒"], ["品質"]),
    "G": ("Goldfish 盲審我們的吸收草稿（2 位審查者）", ["草稿裡沒有根據的說法或和規則衝突的地方"], ["行為上的增益"]),
    "TX": ("在可拋棄環境試跑可執行的成分", ["tripwire：宣告範圍外的寫入、連線、行程"], ["品質"]),
    "T3a-smoke": ("行為 A/B 冒煙測試：有食物（C）對沒有（D），4 案例 × 2 次", ["決定性的退步；早期的沒增益訊號"], ["統計上的增益", "其他 host 或模型"]),
    "T4": ("和現有配方整合（受害者檢查）", ["拉肚子：讓現有 skill 變差"], ["增益"]),
    "P": ("齊平底線：OAW＋食物（C）對 單吃食物（B）", ["齊平或進化的說法"], ["其他 host"]),
    "T3a": ("行為 A/B 完整測試：每組 8 案例 × 5 次", ["這套題庫上校準過的增益或退步"], ["其他任務、長期效果"]),
}


# D13 (PRE-01): which stage each plan step belongs to. Stage 0/1 count against the per-food screening cap; Stage 2
# (and a second host) always asks the owner first; goldfish reviews are digestion-system overhead with their own cap.
PLAN_D13_STAGE = {"T0": 0, "T1": 0, "T2a": 0, "G": "overhead", "TX": 1, "T3a-smoke": 1, "T4": 2, "P": 2, "T3a": 2}
COST_ZH = {"free": "免費", "free (owner time)": "免費（你的時間）", "paid": "付費"}
SECOND_HOST = ("a second host asks the owner first (D13); the Codex half stays untested until the owner logs in to Codex CLI",
               "第二個 host 一律先問你（D13）；你登入 Codex CLI 之前，Codex 的一半一律記成「未測」")


def decide_plan(food: str, derived: dict, historical=(), policy: dict | None = None) -> dict:
    """D11: the system picks the food's tests from its evidence, cheapest first.

    D13: only Stage 0/1 steps are compared with the per-food cap; a Stage 2 step never runs "within policy".
    A step that executes the food needs sandbox level 2, which this machine does not have yet.
    """
    components = derived.get("components", [])
    has_static = bool(derived.get("inputs"))
    executable = [c for c in components if c["disposition"] == "hold" and c["exec_class"] in ("X1", "X1-inline", "X2")]
    candidates = [c for c in components if c["disposition"] == "absorb" or (c["disposition"] == "hold" and c["kind"] in ("skill", "agent", "command"))]
    methods = [c for record in historical for c in record.get("components", []) if c.get("disposition") in ("absorb", "hold")]
    steps = [{"id": "T0", "name": "static checks", "cost": "free", "state": "done" if has_static else "next",
              "can_prove": ["file inventory, license, declared hooks/MCP/scripts, flags"],
              "cannot_prove": ["behavior, quality, runtime safety"], "tokens": None}]
    steps.append({"id": "T1", "name": "offline fit (name collisions, doctor/migrate round trip)", "cost": "free",
                  "state": "not available in v0", "can_prove": ["install compatibility"], "cannot_prove": ["quality"], "tokens": None})
    headline = derived.get("headline")
    status, basis = None, []
    if headline == "toxic":
        status, basis = "no paid test: owner confirmed toxic", ["toxic is final until new evidence and owner review"]
    elif headline == "inedible":
        status, basis = "no paid test: OAW cannot digest this food as shipped", list(derived.get("reasons", []))
    elif headline == "risky" and not (derived.get("flags") or {}).get("open_high"):
        status, basis = "blocked: the owner blocked this food", list(derived.get("reasons", []))
    elif headline == "risky":
        # D28: flags inform, they do not park the food. Triage stays available (and is still needed to copy a
        # flagged part or to confirm toxic), but the plan goes on to the tasting like any other food's.
        steps.append({"id": "T2a", "name": "owner triage of high-severity flags (optional: only to copy a flagged part or confirm toxic)",
                      "cost": "free (owner time)", "state": "optional",
                      "can_prove": ["whether each flag is benign, an allergen or toxic"], "cannot_prove": ["quality"], "tokens": None})
    if status is None and not has_static:
        status, basis = "taste first: free static checks decide the paid plan", ["no static record"]
    elif status is None and derived.get("food_kind") == "paper" and not components and not methods:
        status, basis = "no components yet: " + PAPER_COMPONENTS_NOTE, ["a paper is split into components by a model, not by static rules"]
    elif status is None and not candidates and not methods:
        status, basis = "no paid test needed: nothing absorbable", ["every component is excreted or reference-only"]
    if status is None:
        if methods or candidates:
            steps.append({"id": "G", "name": "goldfish blind review of the absorption drafts (2 reviewers)", "cost": "paid",
                          "state": "planned", "can_prove": ["unsupported claims or rule conflicts in our drafts"],
                          "cannot_prove": ["behavior gain"], "tokens": _tokens(2)})
        if executable:
            steps.append({"id": "TX", "name": f"sandbox trial of {len(executable)} executable part(s) in a disposable environment",
                          "cost": "paid", "state": "planned", "can_prove": ["tripwires: writes, network, processes outside the declared scope"],
                          "cannot_prove": ["quality"], "tokens": _tokens(2 * len(executable))})
        if candidates or methods:
            steps.append({"id": "T3a-smoke", "name": "behavior A/B smoke: with the food (C) vs without (D), 4 cases x 2 runs",
                          "cost": "paid", "state": "planned", "can_prove": ["deterministic regressions; early no-gain signal"],
                          "cannot_prove": ["statistical gain", "other hosts or models"], "tokens": _tokens(16)})
            steps.append({"id": "T4", "name": "integration with the current recipe (victim checks)", "cost": "paid", "state": "planned",
                          "can_prove": ["diarrhea: harm to existing skills"], "cannot_prove": ["gain"], "tokens": _tokens(16)})
            steps.append({"id": "P", "name": "parity floor: OAW with the food (C) vs the food alone (B)", "cost": "paid",
                          "state": "planned", "can_prove": ["parity or evolution claim"], "cannot_prove": ["other hosts"], "tokens": _tokens(16)})
            steps.append({"id": "T3a", "name": "behavior A/B full: 8 cases x 5 runs per arm", "cost": "paid",
                          "state": "only if the smoke shows no deterministic negative", "conditional": True,
                          "can_prove": ["calibrated gain or regression on this suite"], "cannot_prove": ["other tasks, long-term effects"],
                          "tokens": _tokens(80)})
        basis = [f"{len(candidates)} absorbable or skill-type part(s)", f"{len(methods)} historical method proposal(s)",
                 f"{len(executable)} executable part(s) on hold"]
    for step in steps:
        name_zh, can_zh, cannot_zh = PLAN_STEPS_ZH[step["id"]]
        stage = PLAN_D13_STAGE[step["id"]]
        level = None if not step["tokens"] else 2 if step["id"] == "TX" or (step["id"] == "P" and executable) else 1
        step.update(name_zh=name_zh, can_prove_zh=can_zh, cannot_prove_zh=cannot_zh, conditional=bool(step.get("conditional")),
                    cost_zh=COST_ZH.get(step["cost"], step["cost"]), d13_stage=stage, sandbox_level=level,
                    asks_owner=stage == 2)
    paid = [s for s in steps if s["tokens"]]
    paid.sort(key=lambda s: s["tokens"]["max"])
    free = [s for s in steps if not s["tokens"]]
    # The least it can cost is the unconditional steps; a conditional step adds at most its own maximum.
    unconditional = [s for s in paid if not s["conditional"]]
    conditional = [s for s in paid if s["conditional"]]
    total = {"min": sum(s["tokens"]["min"] for s in unconditional), "max": sum(s["tokens"]["max"] for s in paid),
             "unconditional_max": sum(s["tokens"]["max"] for s in unconditional),
             "conditional_max": sum(s["tokens"]["max"] for s in conditional),
             "screening_max": sum(s["tokens"]["max"] for s in paid if s["d13_stage"] in (0, 1)),
             "stage2_max": sum(s["tokens"]["max"] for s in paid if s["d13_stage"] == 2),
             "overhead_max": sum(s["tokens"]["max"] for s in paid if s["d13_stage"] == "overhead"),
             "label": TOKEN_LABEL, "label_zh": TOKEN_LABEL_ZH}
    if status is None:
        if not policy:
            status = "waiting for standing policy"
        elif total["screening_max"] <= policy.get("per_food_token_cap", -1):
            status = "within policy for Stage 0/1 - Stage 2 and a second host ask the owner first; paid runs not enabled in v0"
        else:
            status = "exceeds standing policy for Stage 0/1 - owner approval needed (paid runs not enabled in v0)"
    plan = {"schema_version": SCHEMA_VERSION, "food": food, "decided_by": "system (D11), from evidence; owner sets only the standing policy",
            "headline": headline, "basis": basis, "steps": free + paid, "estimate": total, "status": status,
            "second_host": SECOND_HOST[0], "second_host_zh": SECOND_HOST[1],
            "paid_runs_enabled": False, "policy_sha256": record_sha256(policy) if policy else None}
    plan["plan_id"] = "p-" + record_sha256({k: v for k, v in plan.items() if k != "policy_sha256"})[:12]
    return plan


# --------------------------------------------------------------------------- scout relevance

_STRONG = ("claude code", "claude-code", "claudecode", "codex", "coding agent", "coding-agent", "agent skill", "agent-skill",
           "agentskills", "skill.md", "claude skill", "subagent", "agent harness", "harness", "mcp server", "model context protocol",
           "agents.md", "claude.md", "agentic coding", "ai coding", "cursor rules", "slash command", "claude-plugin")
_UNRELATED = ("video", "youtube", "tiktok", "image generation", "stable diffusion", "comfyui", "music", "audio", "podcast",
              "trading", "crypto", "stock", "wallpaper", "anime", "minecraft", "photo", "voice clone", "text-to-speech",
              "subtitle", "movie", "ebook", "resume")


def relevance(item: dict) -> dict:
    """D4 filter: keep only coding-agent skill/harness repos; stars are not consulted."""
    text = _normalized(" ".join([str(item.get("full_name") or item.get("name") or ""), str(item.get("description") or ""),
                                 " ".join(str(t) for t in item.get("topics") or [])]).replace("_", " "))
    strong = [term for term in _STRONG if term in text]
    unrelated = [term for term in _UNRELATED if re.search(r"\b" + re.escape(term) + r"s?\b", text)]
    if not strong:
        return {"keep": False, "reason": "no coding-agent skill or harness signal"}
    if unrelated and len(strong) < 2:
        return {"keep": False, "reason": f"unrelated domain: {unrelated[0]}"}
    return {"keep": True, "reason": "signals: " + ", ".join(strong[:4])}


# --------------------------------------------------------------------------- imported reports

# Reviews of the drafts that are not Goldfish records; they are listed apart, never as zero-context reviews.
REVIEW_RECORDS = ("skeptic.json",)


def _count(values) -> dict:
    counts = {}
    for value in values:
        key = sanitize_text(value, 30) or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def imported_record(food: str, docs: dict, source_files: list, recorded_at: str) -> dict:
    """Historical-prior evidence from an Elephant/Goldfish digestion directory.

    Whatever the files claim, the record is `imported-report` / `historical-prior`:
    `derive()` ignores it, so it can be shown but never raise a verdict.
    """
    digest = docs.get("digest.json") if isinstance(docs.get("digest.json"), dict) else None
    verify = docs.get("verify.json") if isinstance(docs.get("verify.json"), dict) else None
    ledger = docs.get("components.json") if isinstance(docs.get("components.json"), dict) else None
    scout = docs.get("scout.json") if isinstance(docs.get("scout.json"), dict) else {}
    integration = docs.get("integration.json") if isinstance(docs.get("integration.json"), dict) else None
    proposals = docs.get("proposals.md") if isinstance(docs.get("proposals.md"), str) else None
    lists = lambda doc, key: [x for x in doc.get(key, []) if isinstance(x, dict)] if isinstance(doc.get(key), list) else []
    # A list counts whatever its items are (the real records hold strings); a missing key is None, never 0.
    count = lambda doc, key: len(doc[key]) if isinstance(doc.get(key), list) else None
    elephant = None
    if digest is not None:
        elephant = {"integration_mode": sanitize_text(digest.get("integration_mode"), 60),
                    "what_it_does": sanitize_text(digest.get("what_it_does"), 400),
                    "gates": [{"gate": sanitize_text(g.get("gate"), 60), "verdict": sanitize_text(g.get("verdict"), 20)} for g in lists(digest, "gates")[:40]],
                    "nutrients": count(digest, "nutrients"), "diarrhea_risks": count(digest, "diarrhea_risks"),
                    "proposed_ab_tests": count(digest, "proposed_ab_tests")}
    verified = None
    if verify is not None:
        verified = {"checks": count(verify, "checks"), "by_status": _count(c.get("status") for c in lists(verify, "checks")),
                    "missed_issues": count(verify, "missed_issues"),
                    "integration_mode_agrees": verify.get("integration_mode_agrees") if isinstance(verify.get("integration_mode_agrees"), bool) else None}
    goldfish = []
    for name in sorted(n for n in docs if n.startswith("goldfish-") and isinstance(docs[n], dict)):
        doc = docs[name]
        findings = lists(doc, "findings")
        # D15: zero context is verified, not assumed; a record that does not state its launch shows "not recorded".
        launch_doc = doc.get("launch") if isinstance(doc.get("launch"), dict) else doc
        launch = {key: (sanitize_text(launch_doc.get(source), 160) if isinstance(launch_doc.get(source), (str, int, float, bool)) else None)
                  for key, source in (("method", "launch_method" if launch_doc is doc else "method"), ("host_version", "host_version"),
                                      ("inherited_context", "inherited_context"), ("init_event_check", "init_event_check"))}
        goldfish.append({"reviewer": sanitize_text(doc.get("reviewer") or name[:-5], 40), "file": name, "findings": len(findings),
                         "by_severity": _count(f.get("severity") for f in findings),
                         "summary": sanitize_text(doc.get("verdict_summary") or doc.get("summary"), 300), "launch": launch,
                         "zero_context": "verified" if all(launch.values()) else "not verified"})
    # Other reviews of the drafts (a skeptic pass) are listed apart: they are not Goldfish records.
    reviews = []
    for name in sorted(n for n in docs if n in REVIEW_RECORDS and isinstance(docs[n], dict)):
        findings = lists(docs[name], "findings")
        reviews.append({"file": name, "reviewer": name[:-5], "findings": len(findings), "by_severity": _count(f.get("severity") for f in findings),
                        "summary": sanitize_text(docs[name].get("verdict_summary") or docs[name].get("summary"), 300)})
    documents = [{"name": name, "bytes": len(docs[name].encode("utf-8")),
                  "headings": [sanitize_text(h, 120) for h in re.findall(r"(?m)^#{1,3}\s+(.+)$", docs[name])[:40]]}
                 for name in sorted(n for n in docs if n.endswith(".md") and n != "proposals.md" and isinstance(docs[n], str))]
    components = []

    def hist_id(raw, item):
        return "hist:" + re.sub(r"[^A-Za-z0-9._-]+", "-", raw)[:80] if raw else "hist:" + sha256_bytes(canonical_json(item).encode())[:8]

    def text(value, limit):
        return sanitize_text(value, limit) if isinstance(value, (str, int, float)) else ""

    def entry(cid, name, canonical, revision1, *, history=None, split_of=None):
        """`canonical` holds the fields in force; `revision1` fills a field only while the disposition is unchanged."""
        disposition = canonical.get("disposition") if canonical.get("disposition") in DISPOSITIONS else "hold"
        same = revision1 is not None and revision1.get("disposition") == canonical.get("disposition")

        def pick(key, limit):
            if canonical.get(key) not in (None, ""):
                return text(canonical.get(key), limit)
            return text(revision1.get(key), limit) if same else ""
        corrections = canonical.get("claim_corrections") if isinstance(canonical.get("claim_corrections"), list) else []
        reason = pick("reason", 300) or (text(corrections[0], 300) if corrections else "")
        return {"id": cid, "kind": "method", "name": sanitize_text(name, 120), "disposition": disposition,
                "proposed_by": "elephant (historical-prior)", "oaw_target": pick("oaw_target", 200),
                "reason": reason, "missing_test": pick("missing_test", 200), "level": "historical-prior",
                "revision": 2 if canonical is not revision1 else 1, "history": history, "split_of": split_of}

    # Ledger revision 2: an `after_integration` object is canonical; a split lists parts with their own dispositions.
    # A paper ledger names its units by `what` (a description) rather than `name`.
    for item in lists(ledger or {}, "components")[:300]:
        raw = str(item.get("id") or "")
        label = item.get("name") or (item.get("what") if isinstance(item.get("what"), str) else None)
        after = item.get("after_integration") if isinstance(item.get("after_integration"), dict) else None
        first = text(item.get("disposition"), 20)
        if after is None:
            components.append(entry(hist_id(raw, item), label, item, item))
            continue
        changed = f"revision 1: {first}" if first and first != after.get("disposition") else None
        parts = [p for p in after.get("parts", []) if isinstance(p, dict)] if isinstance(after.get("parts"), list) else []
        if after.get("disposition") == "split" and parts:
            for index, part in enumerate(parts[:20]):
                part_raw = str(part.get("id") or f"{raw}/{index + 1}")
                components.append(entry(hist_id(part_raw, part), f"{label or raw} · {part_raw.rsplit('/', 1)[-1]}", part, None,
                                        history=f"revision 1: {first}, split by integration" if first else "split by integration",
                                        split_of=hist_id(raw, item)))
            continue
        components.append(entry(hist_id(raw, item), label, after, item, history=changed))
    paper = None
    if ledger and ledger.get("food_kind") == "paper":
        # Display only: what the record says it digested (title, version, license); the sealed taste is separate.
        try:
            named = _arxiv_source(str(ledger.get("food") or "")) if ledger.get("food") else None
        except SourceError:
            named = None
        pdf = (ledger.get("pinned_files") or {}).get("paper.pdf") if isinstance(ledger.get("pinned_files"), dict) else None
        authors = ledger.get("authors") if isinstance(ledger.get("authors"), list) else []
        version = text(ledger.get("version"), 10)
        paper = {"arxiv_id": named["arxiv_id"] if named else None, "title": text(ledger.get("title"), 300) or None,
                 "authors": [text(a, 120) for a in authors[:20]], "authors_total": len(authors),
                 "version": version if re.fullmatch(r"v[1-9]\d{0,3}", version) else None,
                 "version_date": text(ledger.get("version_date"), 20) or None, "license": text(ledger.get("license"), 60) or None,
                 "pdf_sha256": pdf if isinstance(pdf, str) and _HEX64.fullmatch(pdf) else None}
    integration_summary = None
    if integration:
        integration_summary = {sanitize_text(k, 40): (sanitize_text(v, 160) if isinstance(v, (str, int, float, bool)) else f"{len(v)} item(s)")
                               for k, v in list(integration.items())[:20] if isinstance(v, (str, int, float, bool, list, dict))}
    commit = next((c for c in ((ledger or {}).get("pinned_commit"), scout.get("commit")) if isinstance(c, str) and re.fullmatch(r"[0-9a-f]{40}", c)), None)
    files_sha = record_sha256(sorted((f["name"], f["sha256"]) for f in source_files))
    return {"schema_version": SCHEMA_VERSION, "evidence_id": f"{food}/imported/{files_sha[:12]}", "food": food,
            "tier": "imported", "mode": "historical-prior", "provenance": "imported-report", "level": "historical-prior",
            "pinned_commit": commit, "source_files": source_files, "elephant": elephant, "verify": verified, "goldfish": goldfish,
            "components": components, "counts": {k: sum(1 for c in components if c["disposition"] == k) for k in DISPOSITIONS},
            "integration": integration_summary, "reviews": reviews, "documents": documents, "paper": paper,
            "proposals": {"bytes": len(proposals.encode("utf-8")),
                          "headings": [sanitize_text(h, 120) for h in re.findall(r"(?m)^#{1,3}\s+(.+)$", proposals)[:40]]} if proposals else None,
            "note": "imported report: historical-prior, shown separately, never counted in a verdict", "recorded_at": recorded_at}


# --------------------------------------------------------------------------- agent tastings and D21 absorptions (D25, D28)
#
# Claude tastes a food in the tasting area (D25) and, under D21, rebuilds the picked units as OAW code with tests on
# the working branch. Both happen outside this engine; `catalog.py record-tasting` and `record-absorption` put
# their results in the ledger as evidence files, so view.json shows real progress (D28.4). The engine checks
# every record twice, when it is recorded and whenever a view is built, so a hand-edited file cannot carry a
# verdict the rules refuse. Neither record changes derive(): the static headline and the copy-absorb holds stay.

TASTING_SCHEMA = "oaw-tasting/1"
ABSORPTION_SCHEMA = "oaw-absorption/1"
# verdict -> Traditional Chinese label. The latest tasting decides; every tasting stays on the card.
TASTING_VERDICTS = {"absorb": "吸收", "plug-in": "插上（接上官方版，不吸收）", "optional": "可選用（不設預設，要用時才叫）",
                    "decline": "不收", "not-shown-better": "沒證明比原生好（不收）", "no-verdict": "沒有判定"}
# D29 (2026-11-06): a tasting's `judgment` (quality against native, cost ratio, cheaper by its PREREG rule, how
# the quality was graded) fixes its outcome; the recorded verdict must match. Outcome -> allowed verdicts.
D29_COST_CAP = 1.5
D29_QUALITY = ("better", "same", "worse")
D29_GRADING = ("double-graded", "mechanical", "single-graded")
D29_OUTCOMES = {"default": ("absorb", "plug-in"), "optional": ("optional",), "excrete": ("decline",)}
D29_OUTCOMES_ZH = {"default": "進預設", "optional": "可選用", "excrete": "排掉"}
# What the owner reads (display only; stored records keep D29_OUTCOMES_ZH). With 4-12 tasks a "same" quality
# means no difference was detected, not that one was ruled out (2026-11-06 research), so it reads 未定.
D29_QUALITY_ZH = {"better": "比原生好", "same": "沒測出差異（未定）", "worse": "比原生差"}
D29_LABELS_ZH = {("default", "better"): "進預設（更好）", ("default", "same"): "進預設（品質未定但比較省）",
                 ("optional", "same"): "可選用（能力未定）", ("optional", "better"): "可選用（更好但很貴）",
                 ("excrete", "same"): "因成本不採用（能力未定）", ("excrete", "worse"): "排掉（比原生差）"}


def d29_label(judgment) -> str | None:
    """The plain verdict label of a D29 judgment, or None for a record made before D29."""
    if not judgment:
        return None
    return D29_LABELS_ZH.get((judgment.get("outcome"), judgment.get("quality")))
# D21 tiers: what makes a unit automatic and what asks the owner.
TIERS = {"A": "A 級：只改機制、不碰模型會讀的文字、不執行食物程式、可還原（D17 允許靜態證據）",
         "B": "B 級：模型會讀的文字，要試吃判定吸收（齊平以上）",
         "C": "C 級：會執行食物程式、新增執行期相依、常設決定沒涵蓋的授權或 CLI 選擇、移除 skill、超出預算：問你"}
RELEASE_STATES = ("pending", "released")
RECORD_FILE_BYTES = 1024 * 1024
_RECORD_LIMITS = {"arms": 12, "models": 8, "units": 300, "commits": 20, "tests": 40}
_DATE = re.compile(r"(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_ARM_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}")
_UNIT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}")
_REF_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")
_TASTING_ID = re.compile(r"t-[0-9a-f]{12}")
_TASTING_KEYS = {"schema", "food", "date", "records", "protocol", "arms", "food_arm_ran", "verdict", "verdict_zh",
                 "blocked_on_owner", "notes", "judgment"}
_ABSORPTION_KEYS = {"schema", "food", "date", "branch", "absorbed", "declined", "held", "release", "blocked_on_owner",
                    "records", "notes"}
# Keys the CLI adds when it stores a record; a stored record is checked against its own id.
_STORED_KEYS = {"tasting_id", "absorption_id", "recorded_at", "provenance", "source_sha256", "food_arm"}
_RESULT_KEYS = ("coverage", "essential_correct", "essential_total", "wrong_claims", "token_median", "tokens_total")


class RecordError(ValueError):
    """A tasting or absorption record the engine refuses; nothing is recorded."""


def _where(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def _keys(doc, allowed: set, prefix: str, kind: str) -> dict:
    if not isinstance(doc, dict):
        raise RecordError(f"{kind}: {prefix or 'the record'} must be a JSON object.")
    unknown = sorted(str(k) for k in doc if k not in allowed)
    if unknown:
        raise RecordError(f"{kind}: unknown field(s) {', '.join(_where(prefix, k) for k in unknown[:5])}; "
                          f"allowed: {', '.join(sorted(allowed))}.")
    return doc


def _rtext(doc: dict, key: str, prefix: str, kind: str, limit: int = 300, required: bool = True):
    value = doc.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        if required:
            raise RecordError(f"{kind}: {_where(prefix, key)} must be nonempty text.")
        return None
    if len(value) > limit:
        raise RecordError(f"{kind}: {_where(prefix, key)} is longer than {limit} characters.")
    return sanitize_text(value, limit)


def _rnumber(doc: dict, key: str, prefix: str, kind: str, *, integer: bool = False, maximum=None, required: bool = True):
    value = doc.get(key)
    if value is None:
        if required:
            raise RecordError(f"{kind}: {_where(prefix, key)} is required.")
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (integer and not isinstance(value, int)):
        raise RecordError(f"{kind}: {_where(prefix, key)} must be a {'whole number' if integer else 'number'}.")
    if value != value or value < 0 or value > (maximum if maximum is not None else 10**12):
        raise RecordError(f"{kind}: {_where(prefix, key)} is out of range (0 to {maximum if maximum is not None else 10**12}).")
    return value


def _rdate(doc: dict, kind: str) -> str:
    value = doc.get("date")
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise RecordError(f"{kind}: date must be YYYY-MM-DD.")
    return value


def _rlist(doc: dict, key: str, prefix: str, kind: str, limit: int, *, required: bool = True) -> list:
    value = doc.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value):
        raise RecordError(f"{kind}: {_where(prefix, key)} must be a nonempty list.")
    if len(value) > limit:
        raise RecordError(f"{kind}: {_where(prefix, key)} lists more than {limit} items.")
    return value


def _rrecords(doc, prefix: str, kind: str, *, required: bool) -> dict | None:
    """Where the evidence lives: a relative path on the records branch and the commit that holds it."""
    if doc is None and not required:
        return None
    ref = _keys(doc, {"path", "commit", "branch"}, prefix, kind)
    path = _rtext(ref, "path", prefix, kind, 240)
    if path.startswith(("/", "~")) or "\\" in path or ":" in path or ".." in path.split("/"):
        raise RecordError(f"{kind}: {prefix}.path must be a relative path inside the repository.")
    commit = ref.get("commit")
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise RecordError(f"{kind}: {prefix}.commit must be 7-40 lowercase hex characters.")
    branch = ref.get("branch", "records")
    if not isinstance(branch, str) or not _REF_NAME.fullmatch(branch):
        raise RecordError(f"{kind}: {prefix}.branch is not a branch name.")
    return {"path": path, "commit": commit, "branch": branch}


def _check_food(doc: dict, food: str, kind: str) -> None:
    named = doc.get("food")
    if named is not None and named != food:
        raise RecordError(f"{kind}: the record names another food ({sanitize_text(named, 64)!r}, not {food!r}).")


def _check_stored(doc: dict, id_key: str, record: dict, prefix: str) -> None:
    """A stored record must still hash to the id it was recorded under: an edited file is refused, never trusted."""
    if id_key in doc:
        expected = prefix + record_sha256(record)[:12]
        if doc[id_key] != expected:
            raise RecordError(f"{id_key} does not match the record's content: the file was edited after it was recorded.")


def validate_tasting(doc, food: str, *, stored: bool = False) -> dict:
    """One agent tasting (schema oaw-tasting/1), normalized; raises RecordError on any refusal.

    D28.3: a verdict other than `no-verdict` needs at least one graded run of the food arm, and the record's
    `food_arm_ran.graded_runs` must agree with the food arm's own count. `no-verdict` must say what blocks it.
    """
    kind = "Tasting record"
    if not isinstance(doc, dict) or doc.get("schema") != TASTING_SCHEMA:
        raise RecordError(f"Not a tasting record: schema must be {TASTING_SCHEMA}.")
    _keys(doc, _TASTING_KEYS | (_STORED_KEYS if stored else set()), "", kind)
    _check_food(doc, food, kind)
    protocol_doc = _keys(doc.get("protocol"), {"models", "corpus", "questions", "repeats", "grading", "host"}, "protocol", kind)
    models = []
    for index, model in enumerate(_rlist(protocol_doc, "models", "protocol", kind, _RECORD_LIMITS["models"])):
        if not isinstance(model, str) or not model.strip() or len(model) > 80:
            raise RecordError(f"{kind}: protocol.models[{index}] must be a model name.")
        models.append(sanitize_text(model, 80))
    questions = _keys(protocol_doc.get("questions"), {"count", "sha256", "file"}, "protocol.questions", kind)
    if not isinstance(questions.get("sha256"), str) or not _HEX64.fullmatch(questions["sha256"]):
        raise RecordError(f"{kind}: protocol.questions.sha256 must be 64 lowercase hex characters (the frozen questions).")
    protocol = {"models": models, "corpus": _rtext(protocol_doc, "corpus", "protocol", kind, 300),
                "questions": {"count": _rnumber(questions, "count", "protocol.questions", kind, integer=True, maximum=10000),
                              "sha256": questions["sha256"],
                              "file": _rtext(questions, "file", "protocol.questions", kind, 200, required=False)},
                "repeats": _rnumber(protocol_doc, "repeats", "protocol", kind, integer=True, maximum=1000),
                "grading": _rtext(protocol_doc, "grading", "protocol", kind, 200, required=False),
                "host": _rtext(protocol_doc, "host", "protocol", kind, 200, required=False)}
    if protocol["questions"]["count"] < 1 or protocol["repeats"] < 1:
        raise RecordError(f"{kind}: protocol.questions.count and protocol.repeats must be at least 1.")
    arms, seen = [], set()
    for index, raw in enumerate(_rlist(doc, "arms", "", kind, _RECORD_LIMITS["arms"])):
        where = f"arms[{index}]"
        arm = _keys(raw, {"id", "label", "food_arm", "runs", "graded_runs", "results"}, where, kind)
        arm_id = arm.get("id")
        if not isinstance(arm_id, str) or not _ARM_ID.fullmatch(arm_id) or arm_id in seen:
            raise RecordError(f"{kind}: {where}.id must be a unique short id (letters, digits, . _ -).")
        seen.add(arm_id)
        if not isinstance(arm.get("food_arm", False), bool):
            raise RecordError(f"{kind}: {where}.food_arm must be true or false.")
        runs = _rnumber(arm, "runs", where, kind, integer=True, maximum=100000)
        graded = _rnumber(arm, "graded_runs", where, kind, integer=True, maximum=100000)
        if graded > runs:
            raise RecordError(f"{kind}: {where}.graded_runs ({graded}) is more than its runs ({runs}).")
        results_doc = _keys(arm.get("results", {}), set(_RESULT_KEYS), f"{where}.results", kind)
        results = {key: _rnumber(results_doc, key, f"{where}.results", kind, required=False,
                                 maximum=1 if key == "coverage" else None, integer=key == "wrong_claims")
                   for key in _RESULT_KEYS}
        arms.append({"id": arm_id, "label": _rtext(arm, "label", where, kind, 120, required=False),
                     "food_arm": bool(arm.get("food_arm", False)), "runs": runs, "graded_runs": graded, "results": results})
    food_arms = [a for a in arms if a["food_arm"]]
    if len(food_arms) != 1:
        raise RecordError(f"{kind}: exactly one arm must be the food arm (food_arm: true); found {len(food_arms)}.")
    ran_doc = _keys(doc.get("food_arm_ran"), {"graded_runs", "evidence"}, "food_arm_ran", kind)
    ran = {"graded_runs": _rnumber(ran_doc, "graded_runs", "food_arm_ran", kind, integer=True, maximum=100000),
           "evidence": _rtext(ran_doc, "evidence", "food_arm_ran", kind, 240, required=False)}
    if ran["graded_runs"] != food_arms[0]["graded_runs"]:
        raise RecordError(f"{kind}: food_arm_ran.graded_runs ({ran['graded_runs']}) does not match the food arm "
                          f"{food_arms[0]['id']!r} ({food_arms[0]['graded_runs']} graded runs).")
    verdict = doc.get("verdict")
    if verdict not in TASTING_VERDICTS:
        raise RecordError(f"{kind}: verdict must be one of {', '.join(TASTING_VERDICTS)}.")
    owner = _rtext(doc, "blocked_on_owner", "", kind, 300, required=False)
    notes = _rtext(doc, "notes", "", kind, 2000, required=False)
    if verdict != "no-verdict" and ran["graded_runs"] < 1:
        raise RecordError("Refused: no verdict without the food arm installed and run (D28): the food arm "
                          f"{food_arms[0]['id']!r} has no graded run. Record it as no-verdict and say what blocks it.")
    if verdict == "no-verdict" and not (owner or notes):
        raise RecordError("A no-verdict tasting must say what blocks it: blocked_on_owner (the owner's part) or notes.")
    if owner and verdict in ("decline", "not-shown-better"):
        raise RecordError(f"{kind}: blocked_on_owner is only for absorb, plug-in, optional or no-verdict; a {verdict} leaves nothing to wait for.")
    judgment = _judgment(doc.get("judgment"), verdict, kind, stored=stored)
    record = {"schema": TASTING_SCHEMA, "food": food, "date": _rdate(doc, kind),
              "records": _rrecords(doc.get("records"), "records", kind, required=True), "protocol": protocol,
              "arms": arms, "food_arm": food_arms[0]["id"], "food_arm_ran": ran, "verdict": verdict,
              "verdict_zh": _rtext(doc, "verdict_zh", "", kind, 300), "blocked_on_owner": owner, "notes": notes}
    if judgment is not None:
        record["judgment"] = judgment
    if stored:
        _check_stored(doc, "tasting_id", record, "t-")
    return record


def d29_outcome(quality: str, cost_ratio: float, cheaper: bool) -> str:
    """D29: default, optional or excrete from quality against native and the cost ratio (food / native)."""
    if quality == "worse":
        return "excrete"
    if quality == "better":
        return "default" if cost_ratio <= D29_COST_CAP else "optional"
    if cheaper:
        return "default"
    return "optional" if cost_ratio <= D29_COST_CAP else "excrete"


def _judgment(raw, verdict: str, kind: str, *, stored: bool = False):
    """The D29 judgment of a tasting, checked against its verdict; None for a record made before D29.

    `optional` exists only under D29, so it needs a judgment; a judgment never goes with `not-shown-better` or
    `no-verdict`. An AI-graded difference (better or worse) counts only when it held in two gradings (D29.1).
    """
    if raw is None:
        if verdict == "optional":
            raise RecordError(f"{kind}: an optional verdict needs its D29 judgment (quality, cost_ratio, cheaper, grading).")
        return None
    where = "judgment"
    doc = _keys(raw, {"quality", "cost_ratio", "cheaper", "grading", "conditions", "basis"}
                | ({"outcome", "outcome_zh"} if stored else set()), where, kind)
    quality, grading = doc.get("quality"), doc.get("grading")
    if quality not in D29_QUALITY:
        raise RecordError(f"{kind}: judgment.quality must be one of {', '.join(D29_QUALITY)}.")
    if grading not in D29_GRADING:
        raise RecordError(f"{kind}: judgment.grading must be one of {', '.join(D29_GRADING)}.")
    cost = _rnumber(doc, "cost_ratio", where, kind, maximum=100000)
    if cost <= 0:
        raise RecordError(f"{kind}: judgment.cost_ratio must be the food's tokens over native's (above 0).")
    cheaper = doc.get("cheaper", False)
    if not isinstance(cheaper, bool):
        raise RecordError(f"{kind}: judgment.cheaper must be true or false (the PREREG's cheaper rule).")
    if cheaper and (quality != "same" or cost >= 1):
        raise RecordError(f"{kind}: judgment.cheaper needs quality same and a cost ratio below 1.")
    if quality != "same" and grading == "single-graded":
        raise RecordError(f"Refused: an AI-graded difference counts only if it holds in two gradings (D29); "
                          f"a single grading can only say quality same, not {quality}.")
    conditions = _rnumber(doc, "conditions", where, kind, integer=True, maximum=100, required=False)
    if verdict in ("not-shown-better", "no-verdict"):
        raise RecordError(f"{kind}: a D29 judgment ends in absorb, plug-in, optional or decline, not {verdict}.")
    outcome = d29_outcome(quality, cost, cheaper)
    if verdict not in D29_OUTCOMES[outcome]:
        raise RecordError(f"Refused: the verdict does not match D29: quality {quality}, cost {cost:g}x native"
                          + (", cheaper" if cheaper else "") + f" -> {outcome} ({D29_OUTCOMES_ZH[outcome]}), "
                          f"which is recorded as {' or '.join(D29_OUTCOMES[outcome])}, not {verdict}.")
    return {"quality": quality, "cost_ratio": cost, "cheaper": cheaper, "grading": grading,
            "conditions": conditions, "outcome": outcome, "outcome_zh": D29_OUTCOMES_ZH[outcome],
            "basis": _rtext(doc, "basis", where, kind, 400, required=False)}


def tasting_id(record: dict) -> str:
    return "t-" + record_sha256(record)[:12]


def _unit(raw, where: str, kind: str, *, absorbed: bool) -> dict:
    allowed = {"id", "name", "tier", "commits", "tests", "evidence", "owner_approval"} if absorbed else {"id", "name", "reason"}
    unit = _keys(raw, allowed, where, kind)
    unit_id = unit.get("id")
    if not isinstance(unit_id, str) or not _UNIT_ID.fullmatch(unit_id):
        raise RecordError(f"{kind}: {where}.id must be a unit id (letters, digits and . _ : / + -, at most 160).")
    name = _rtext(unit, "name", where, kind, 200, required=False)
    if not absorbed:
        return {"id": unit_id, "name": name, "reason": _rtext(unit, "reason", where, kind, 300)}
    tier = unit.get("tier")
    if tier not in TIERS:
        raise RecordError(f"{kind}: {where}.tier must be A, B or C (D21).")
    commits = _rlist(unit, "commits", where, kind, _RECORD_LIMITS["commits"])
    if not all(isinstance(c, str) and _COMMIT.fullmatch(c) for c in commits):
        raise RecordError(f"{kind}: {where}.commits must be commit ids (7-40 lowercase hex characters).")
    tests = []
    for index, test in enumerate(_rlist(unit, "tests", where, kind, _RECORD_LIMITS["tests"])):
        if not isinstance(test, str) or not test.strip() or len(test) > 200:
            raise RecordError(f"{kind}: {where}.tests[{index}] must name a test (D21: code and tests are the record).")
        tests.append(sanitize_text(test, 200))
    evidence = _keys(unit.get("evidence"), {"basis", "tasting"}, f"{where}.evidence", kind)
    tasting = evidence.get("tasting")
    if tasting is not None and (not isinstance(tasting, str) or not _TASTING_ID.fullmatch(tasting)):
        raise RecordError(f"{kind}: {where}.evidence.tasting must be a recorded tasting id (t- and 12 hex characters).")
    return {"id": unit_id, "name": name, "tier": tier, "commits": list(dict.fromkeys(commits)), "tests": tests,
            "evidence": {"basis": _rtext(evidence, "basis", f"{where}.evidence", kind, 300), "tasting": tasting},
            "owner_approval": _rtext(unit, "owner_approval", where, kind, 300, required=False)}


def validate_absorption(doc, food: str, tastings=(), *, stored: bool = False) -> dict:
    """One D21 absorption record (schema oaw-absorption/1), normalized; raises RecordError on any refusal.

    `tastings` are the food's valid tasting records. A paper has no installable food arm, so nothing here needs
    one: tier A rests on static evidence (D17, D21); a tier-B unit names a recorded tasting of this food whose
    verdict is absorb; a tier-C unit is absorbed only with the owner's approval written down (D21).
    """
    kind = "Absorption record"
    if not isinstance(doc, dict) or doc.get("schema") != ABSORPTION_SCHEMA:
        raise RecordError(f"Not an absorption record: schema must be {ABSORPTION_SCHEMA}.")
    _keys(doc, _ABSORPTION_KEYS | (_STORED_KEYS if stored else set()), "", kind)
    _check_food(doc, food, kind)
    branch = doc.get("branch")
    if not isinstance(branch, str) or not _REF_NAME.fullmatch(branch):
        raise RecordError(f"{kind}: branch must name the branch that holds the commits.")
    units, seen = {}, set()
    for section in ("absorbed", "declined", "held"):
        units[section] = []
        for index, raw in enumerate(_rlist(doc, section, "", kind, _RECORD_LIMITS["units"], required=False)):
            unit = _unit(raw, f"{section}[{index}]", kind, absorbed=section == "absorbed")
            if unit["id"] in seen:
                raise RecordError(f"{kind}: unit {unit['id']!r} is listed twice.")
            seen.add(unit["id"])
            units[section].append(unit)
    if not seen:
        raise RecordError(f"{kind}: list at least one unit under absorbed, declined or held.")
    verdicts = {t["tasting_id"]: t["verdict"] for t in tastings or () if isinstance(t, dict) and t.get("tasting_id")}
    for unit in units["absorbed"]:
        if unit["tier"] == "B" and verdicts.get(unit["evidence"]["tasting"]) != "absorb":
            raise RecordError(f"A tier-B unit ({unit['id']!r}, model-facing text) is absorbed only with a recorded tasting of this "
                              "food whose verdict is absorb (D17, D21): name its tasting id in evidence.tasting.")
        if unit["tier"] == "C" and not unit["owner_approval"]:
            raise RecordError(f"A tier-C unit ({unit['id']!r}) needs the owner's decision first (D21): record it under held with "
                              "blocked_on_owner, or write where the owner approved it in owner_approval.")
    release_doc = _keys(doc.get("release", {"state": "pending"}), {"state", "pr", "ref"}, "release", kind)
    if release_doc.get("state", "pending") not in RELEASE_STATES:
        raise RecordError(f"{kind}: release.state must be pending or released.")
    record = {"schema": ABSORPTION_SCHEMA, "food": food, "date": _rdate(doc, kind), "branch": branch, **units,
              "release": {"state": release_doc.get("state", "pending"), "pr": _rtext(release_doc, "pr", "release", kind, 200, required=False),
                          "ref": _rtext(release_doc, "ref", "release", kind, 200, required=False)},
              "blocked_on_owner": _rtext(doc, "blocked_on_owner", "", kind, 300, required=False),
              "records": _rrecords(doc.get("records"), "records", kind, required=False),
              "notes": _rtext(doc, "notes", "", kind, 2000, required=False)}
    if stored:
        _check_stored(doc, "absorption_id", record, "a-")
    return record


def absorption_id(record: dict) -> str:
    return "a-" + record_sha256(record)[:12]


def unit_aliases(unit_id: str) -> set:
    """A unit id as a record writes it and as an imported report stores it (hist:<id with / and other marks as ->)."""
    return {unit_id, "hist:" + re.sub(r"[^A-Za-z0-9._-]+", "-", unit_id)[:80]}


def _record_order(record: dict) -> tuple:
    return (str(record.get("date") or ""), str(record.get("recorded_at") or ""), str(record.get("tasting_id") or record.get("absorption_id") or ""))


def food_records(evidence, food: str) -> dict:
    """The food's valid tastings and absorptions (oldest first) and the stored records the engine refuses, with why."""
    tastings, absorptions, refused = [], [], []
    for record in evidence or ():
        kind = evidence_class(record)
        if kind == "tasting":
            try:
                tastings.append({**validate_tasting(record, food, stored=True), "tasting_id": record.get("tasting_id"),
                                 "recorded_at": record.get("recorded_at")})
            except RecordError as exc:
                refused.append({"kind": "tasting", "id": sanitize_text(record.get("tasting_id"), 20) or None, "reason": sanitize_text(str(exc), 300)})
    tastings.sort(key=_record_order)
    for record in evidence or ():
        if evidence_class(record) == "absorption":
            try:
                absorptions.append({**validate_absorption(record, food, tastings, stored=True),
                                    "absorption_id": record.get("absorption_id"), "recorded_at": record.get("recorded_at")})
            except RecordError as exc:
                refused.append({"kind": "absorption", "id": sanitize_text(record.get("absorption_id"), 20) or None,
                                "reason": sanitize_text(str(exc), 300)})
    absorptions.sort(key=_record_order)
    return {"tastings": tastings, "absorptions": absorptions, "refused": refused}


def tasting_summary(record: dict) -> dict:
    """A tasting as the card shows it; numbers stay as recorded, with the protocol they were measured under."""
    return {"id": record.get("tasting_id"), "date": record["date"], "recorded_at": record.get("recorded_at"),
            "verdict": record["verdict"], "verdict_label_zh": TASTING_VERDICTS[record["verdict"]], "verdict_zh": record["verdict_zh"],
            "records": record["records"], "protocol": record["protocol"], "arms": record["arms"], "food_arm": record["food_arm"],
            "food_arm_graded_runs": record["food_arm_ran"]["graded_runs"], "food_arm_evidence": record["food_arm_ran"]["evidence"],
            "blocked_on_owner": record["blocked_on_owner"], "notes": record["notes"], "judgment": record.get("judgment")}


def absorption_summary(records: list) -> dict | None:
    """Every D21 absorption of one food merged by unit (a later record wins for the same unit), plus the records."""
    if not records:
        return None
    units = {}
    for record in records:
        release = record["release"]
        for section, outcome in (("absorbed", "absorbed"), ("declined", "declined"), ("held", "held")):
            for unit in record[section]:
                units[unit["id"]] = {**unit, "outcome": outcome, "branch": record["branch"], "date": record["date"],
                                     "release": release["state"] if outcome == "absorbed" else None,
                                     "record": record.get("absorption_id")}
    ordered = sorted(units.values(), key=lambda u: ({"absorbed": 0, "held": 1, "declined": 2}[u["outcome"]], u["id"]))
    absorbed = [u for u in ordered if u["outcome"] == "absorbed"]
    latest = records[-1]
    return {"units": ordered, "absorbed": len(absorbed), "declined": sum(1 for u in ordered if u["outcome"] == "declined"),
            "held": sum(1 for u in ordered if u["outcome"] == "held"),
            "release_pending": sum(1 for u in absorbed if u["release"] != "released"),
            "branches": sorted({u["branch"] for u in absorbed}), "blocked_on_owner": latest["blocked_on_owner"],
            "records": [{"id": r.get("absorption_id"), "date": r["date"], "branch": r["branch"], "release": r["release"],
                         "records": r["records"], "notes": r["notes"],
                         "counts": {k: len(r[k]) for k in ("absorbed", "declined", "held")}} for r in records]}


# --------------------------------------------------------------------------- view model

def historical_summary(record: dict) -> dict:
    """Display-only digest of an imported report; values are already sanitized."""
    return {"level": "historical-prior", "note": "imported report; not counted in any verdict",
            "evidence_id": record.get("evidence_id"), "source_files": record.get("source_files", []),
            "elephant": record.get("elephant"), "verify": record.get("verify"), "goldfish": record.get("goldfish", []),
            "components": record.get("components", []), "counts": record.get("counts", {}),
            "integration": record.get("integration"), "proposals": record.get("proposals"),
            "reviews": record.get("reviews", []), "documents": record.get("documents", []), "paper": record.get("paper")}


# --------------------------------------------------------------------------- intake pipeline (D19)
#
# The one stage table of the official skill-intake process (docs/SKILL_INTAKE.md). build_view() maps every
# food onto it and writes both into view.json; the web page, `catalog.py menu` and oaw_status.py draw only that.
# automation: automated (the engine runs it by itself today), agent (Claude does it, D28: the default actor at
# every stop), owner (waits for the owner), mixed (more than one kind), planned (part of the process, not done by
# anyone yet: drawn, never the current stage, no action).

PIPELINE_AUTOMATION = {"automated": "自動", "agent": "自動（Claude 接手）", "owner": "需要你", "mixed": "部分自動",
                       "planned": "規劃中"}
# Per-food stage state -> (symbol, Traditional Chinese); every renderer uses these. `partial`: a passed stage
# whose planned steps never ran (so ● would overclaim); `removed`: the food's parts were removed from the build.
PIPELINE_STATES = {"done": ("●", "完成"), "partial": ("◐", "部分完成"), "current": ("◉", "目前"), "blocked": ("⊗", "卡住"),
                   "removed": ("⊖", "已移除"), "todo": ("○", "還沒到"), "planned": ("┄", "規劃中"), "skipped": ("–", "不需要")}
# The organ each stage is drawn as on the page's digestive tract (D23); a caption, never a claim about the stage.
PIPELINE_ORGANS_ZH = {"intake": "口", "quarantine": "食道", "static": "胃", "plan": "十二指腸", "review": "肝", "test": "小腸",
                      "sort": "大腸", "approve": "門靜脈", "build": "全身"}
# Who a food waits on (the page draws it as the food's badge). D28: the agent is the default actor, so
#   agent    = Claude takes the next step (taste, retaste, rebuild, record); not the owner's job;
#   owner    = only the owner can move it (blue "!"): an entry choice, a tier-C question (D21), an owner-only
#              prerequisite (a login, a token, a standing rule), or removing a skill;
#   release  = built on the working branch; the owner's release (merging the PR) decides the whole branch at once,
#              never food by food;
#   optional = only optional owner decisions are left (grey "?");
#   planned  = it waits for a step nobody can run today (kept for the renderers; D28 left no such stop);
#   none     = at rest.
# A taste running right now is live page state (status.json), never view data.
PIPELINE_WAITING_ZH = {"owner": "等你", "agent": "自動（Claude 接手）", "release": "等發布（合併 PR 時一次決定）",
                       "optional": "只有可選的決定", "planned": "等規劃中的步驟（還沒自動化）", "none": "沒有待辦"}
# The one line every agent-waiting blocker adds to what the records cannot say.
AGENT_WHEN_ZH = "Claude 什麼時候接手：沒有排程，在下一次 Claude 工作階段處理（D28）"


def _stage(sid, label_zh, label, automation, decisions, summary_zh, steps, actions):
    return {"id": sid, "label_zh": label_zh, "label": label, "organ_zh": PIPELINE_ORGANS_ZH[sid], "automation": automation,
            "decisions": list(decisions), "summary_zh": summary_zh,
            "steps": [{"label_zh": text, "automation": kind} for text, kind in steps], "actions": list(actions)}


# The two inlets are the front of stage 1 (入口) and fall under its decision (D4).
PIPELINE_INLETS = (
    {"id": "scout", "label_zh": "每週偵查 → 相關性過濾 → 你確認",
     "steps": [{"label_zh": "你按「立即偵查」，每週一次：沒有排程，漏掉的一週就看不到那週推送的 repo", "automation": "owner"},
               {"label_zh": "系統依更新時間搜尋 GitHub 最近 7 天推送的 repo，只記錄候選", "automation": "automated"},
               {"label_zh": "相關性過濾：和 coding agent skill／harness 無關的不經審查就濾掉；星數只決定排序", "automation": "automated"},
               {"label_zh": "你勾選要試哪些", "automation": "owner"}]},
    {"id": "named", "label_zh": "你點名",
     "steps": [{"label_zh": "你給 GitHub repo 或 arXiv 論文的網址，可以一次很多個", "automation": "owner"}]},
)

PIPELINE_STAGES = (
    _stage("intake", "入口", "intake", "mixed", ("D4",),
           "你勾選或點名就是同意試吃（D4）：兩條入口匯成一份食物清單，同一個 repo 或同一篇論文只收一次，接著立刻免費試吃。",
           (("你勾選偵查候選或點名 repo／論文：這就是確認", "owner"), ("批次去重：同一個 repo 只收一次，同一篇論文的各版本也只收一次", "automated"),
            ("確認後立刻送去免費試吃，不再逐樣問你", "automated")), ("taste", "forget")),
    _stage("quarantine", "封存", "quarantine", "automated", ("D7",),
           "repo 固定在 pinned SHA、論文固定在 arXiv 版本＋sha256，唯讀封存在專案外的 LAB_HOME；不解壓、不 import、不執行。",
           (("repo：hardened git fetch，固定 commit", "automated"),
            ("論文：只用 https 抓 arXiv 中繼資料和固定版本的 PDF（有大小和時間上限），記 sha256；PDF 只檢查開頭，不解析", "automated"),
            ("唯讀 tar，放在專案外", "automated")), ("taste", "forget")),
    _stage("static", "靜態", "static checks", "mixed", ("D5", "D7"),
           "免費靜態檢查，把食物拆成成分；靜態規則只舉旗，不判有毒。旗標只供參考，不擋食物（D28）：下一步是 Claude 試吃。",
           (("repo：檔案角色、授權、hooks／MCP／腳本、旗標；論文：標題、作者、版本、授權", "automated"),
            ("把 repo 拆成成分（論文的單位由 Claude 當 Elephant 拆，或匯入紀錄）", "automated"),
            ("旗標交給重建和 Goldfish 盲審；食物接著送去試吃區（D21、D25、D28）", "agent"),
            ("可選：你分流高嚴重度旗標（終端確認碼）；只有要照原樣複製帶旗標的成分或確認有毒時才需要", "owner")),
           ("taste", "triage", "forget")),
    _stage("plan", "計畫", "plan", "mixed", ("D10", "D11"), "系統依證據擬測試計畫，最便宜、又能分辨的測試排前面；Elephant 擬吸收提案。",
           (("系統測試計畫：依證據自動產生", "automated"),
            ("Elephant 依紀錄的決定擬吸收提案，也替論文拆成分（今天只能匯入，標成歷史證據，不計入判定）", "planned")), ()),
    _stage("review", "盲審", "blind review", "planned", ("D10", "D15"), "Goldfish 在驗證過的零脈絡下盲審我們的草稿，Elephant 解決發現。",
           (("Goldfish 零脈絡盲審（啟動 recipe、argv、init event 都要記錄）", "planned"), ("Elephant 解決發現", "planned")), ()),
    _stage("test", "實測", "tests", "mixed", ("D11", "D13", "D25"),
           "Claude 在試吃區試吃（D25、D28）：官方安裝、每一組都跑、盲評、照事先寫死的規則判定，結果用 record-tasting 記錄；"
           "食物組沒跑就沒有判定。引擎自己的測試在常設政策內由便宜到貴跑，還是規劃中。",
           (("Claude 在試吃區試吃：題目先凍結、每一組（原生、食物、OAW 版本）都跑、盲評，記成試吃紀錄", "agent"),
            ("離線整合 T1：名稱碰撞、doctor／migrate 往返", "planned"), ("可拋棄沙箱試跑 TX（level 2）", "planned"),
            ("行為 A/B：模型面向的文字要過", "planned"), ("整合檢查 T4：退步、觸發衝突、context 預算、指示衝突", "planned"),
            ("齊平底線 P：OAW 吃完 對 單吃食物（C ≥ B）", "planned")), ("forget",)),
    _stage("sort", "分流", "verdicts", "mixed", ("D2", "D5", "D16", "D17", "D18"),
           "每個成分判定吸收／排掉／暫留，附原因和證據等級；整合檢查和齊平底線的關口在這裡套用。",
           (("成分判定（今天只有靜態量測）", "automated"), ("模型面向的文字和機制拆開：文字過 A/B 才能吸收", "automated"),
            ("試吃判定：吸收、插上、不收、沒證明比較好，或沒有判定（照試吃紀錄）", "agent"),
            ("套用整合檢查（T4）和齊平底線（P）的關口", "planned"),
            ("沒建的項目寫「未量測（規劃：<等級>）」，規劃的等級另放一欄", "planned")), ("forget",)),
    _stage("approve", "核准", "approval", "mixed", ("D7", "D11", "D21"),
           "D21：Claude 把挑中的單位重建成 OAW 程式和測試（A 級靜態證據就夠、B 級要試吃判定吸收），用 record-absorption 記錄；"
           "只有 C 級問你。系統不會自動安裝或套用；照原樣複製吸收是可選的舊流程。",
           (("Claude 依 D21 把挑中的單位重建成 OAW 程式和測試，記成吸收紀錄", "agent"),
            ("C 級（執行食物程式、新增執行期相依、常設決定沒涵蓋的授權或 CLI 選擇、移除 skill、超出預算）問你", "owner"),
            ("可選：照原樣複製吸收（你勾選成分，先預覽再確認）", "owner")), ("absorb", "forget")),
    _stage("build", "版本", "build", "mixed", ("D3", "D6", "D12", "D14"),
           "每次吸收或移除都產生 2.0.0+build.N.<hash7> 和還原點，列出和預設比的效果與證據等級；可一鍵線性還原，任何 skill（含 EGM）都能移除。",
           (("發布：你合併 PR，整個分支一次決定，不是逐樣核准（D21、D28）", "owner"),
            ("還原點 → 安裝 → 版本 → 和預設比", "automated"),
            ("吸收時照原樣複製 skill 文字，附上食物的授權檔和出處說明（重新實作成 OAW 部件還沒做）", "automated"),
            ("還原到任何一版（線性：只有移除版本，沒有逐項開關）", "owner"), ("移除（含 EGM）、加回：再加回要重新測試", "owner"),
            ("每版引用清單：用在哪裡／沒採用的原因", "planned"),
            ("release 目標：2.0.0 打 tag 之後，相容的新增進 2.x、不相容的等 3.0.0", "planned")),
           ("remove-food", "restore", "taste", "absorb", "forget")),
)
PIPELINE_ORDER = tuple(stage["id"] for stage in PIPELINE_STAGES)
# A stage that is not planned as a whole but has planned steps is `partial` once passed: ● would claim those steps ran.
PARTIAL_STAGES = frozenset(s["id"] for s in PIPELINE_STAGES
                           if s["automation"] != "planned" and any(step["automation"] == "planned" for step in s["steps"]))
# Action id -> the engine action it calls (the page's /api/action/NAME, the menu's run_action name), its label, and
# where it runs. A terminal action needs an owner code: the page shows it as text; only the menu and the CLI run it.
PIPELINE_ACTIONS = {
    "taste": {"endpoint": "taste", "label_zh": "送去試吃", "where": "both"},
    "forget": {"endpoint": "forget", "label_zh": "忘掉這樣食物", "where": "both"},
    "triage": {"endpoint": "triage", "label_zh": "分流旗標（終端確認碼）", "where": "terminal"},
    "absorb": {"endpoint": "absorb", "label_zh": "吸收選中的成分…", "where": "both"},
    "remove-food": {"endpoint": "remove", "label_zh": "移除", "where": "both"},
    "restore": {"endpoint": "restore", "label_zh": "還原到這版", "where": "both"},
}
PIPELINE_EMPTY_ZH = "還沒有食物：在「你點名」貼上 GitHub 網址或 arXiv 論文網址按「送去試吃」，或在「每週偵查」按「立即偵查」再勾選候選。"
# status.json stages a running taste reports -> the pipeline stage the page shows the food on meanwhile.
LIVE_STAGES = {"ingest": "intake", "quarantine": "quarantine", "static": "static"}


# The rule or decision a food's blocker rests on (docs/SKILL_INTAKE.md), for the page's blocker explanation.
BLOCKER_BASIS_ZH = {
    "D4": "D4：你勾選或點名就是同意試吃；只登記（--no-taste）或匯入時登記的食物，要按「送去試吃」",
    "D5": "D5：判定以成分為單位，每個成分都要有證據",
    "D6": "D6：任何吸收的 skill 都能移除；移除後再加回要重新測試",
    "D7": "D7：不自動安裝或套用；食物只封存在專案外，絕不執行",
    "D28-static": ("D21、D25、D28：旗標只供參考，不擋食物：挑中的單位會重建成 OAW 程式和測試（不複製食物的程式碼），"
                   "食物只在試吃區執行，旗標交給重建和 Goldfish 盲審。分流是可選的：只有要照原樣複製帶旗標的成分、或確認有毒時才需要"),
    "D11": "D7、D11：系統不會自動安裝或套用；照原樣複製吸收要你勾選、預覽、確認（可選的舊流程）",
    "D14": "D14：還原是線性的：只有移除版本，沒有逐項開關",
    "D17": "D17：模型面向的 skill 文字要過行為 A/B 才能吸收；Claude 的試吃（D25）就是這個 A/B",
    "D21": "D21：A 級（只改機制）靜態證據就能吸收、B 級（模型會讀的文字）要試吃判定吸收、C 級問你；吸收是 Claude 重建成 OAW 程式和測試",
    "D25": "D25、D28：沒有試吃就沒有判定；Claude 在試吃區官方安裝、每一組都跑、盲評，再用 record-tasting 記錄",
    "D28-verdict": "D28：食物組沒有裝起來跑過、沒有評分過的執行，就沒有判定；「天花板」推論不能取代實際跑",
    "D29": "D29：品質和原生比（AI 評分的差距要兩次評分都成立）、成本和原生比；更好且不超過 1.5 倍 → 進預設，齊平或更好但很貴 → 可選用，變差或齊平但超過 1.5 倍 → 排掉",
    "D28-owner": "D28：只有入口、發布、C 級問題和只有你能做的前置（登入、token、常設規則）才等你",
    "release": "D21、D28：發布是整個分支一次決定：你合併 PR，這些單位一起進正式版本；不是逐樣核准",
    "paper": "D5、D21：論文的想法要重新實作成 OAW 程式和測試，不複製原文；替論文拆單位由 Claude 當 Elephant 做（D28），引擎不會自己拆",
    "rescan": "第 3 站：掃描規則更新後，舊的試吃紀錄要用新規則再試吃（免費）才能吸收",
    "backlog": "第 8 站：匯入的歷史提案只記成待辦，不改任何檔案，也不產生新版本",
    "toxic": "只有你能判「有毒」；你確認後整樣排掉",
    "import": "這樣食物是匯入紀錄時登記的；匯入只讀紀錄，不試吃也不連網",
}
# A hold the owner can clear today (flags: catalog.py menu → 12); other missing tests wait for planned steps.
OWNER_MISSING = frozenset({"triage"})


def can_absorb(part: dict) -> bool:
    """One rule for the page, the menu and the CLI: an absorb proposal not in the build and not decided yet.

    A removed part counts again only after a taste recorded after its removal (D6: re-adding needs testing again).
    """
    if part.get("disposition") != "absorb" or part.get("in_current_build"):
        return False
    return not part.get("decision") or (part.get("decision") == "removed" and bool(part.get("retested_after_remove")))


def _flag_lines(card: dict, limit: int = 3) -> list:
    """Open high-severity flags as '<rule> <path>:<line>：<meaning>' (the card's own flag list)."""
    open_high = [f for f in card.get("flag_list") or [] if isinstance(f, dict) and f.get("severity") == "high" and not f.get("triage")]
    lines = [f"{sanitize_text(f.get('rule'), 20)} {sanitize_text(f.get('path'), 80)}" + (f":{f['line']}" if isinstance(f.get("line"), int) else "")
             + "：" + sanitize_text(f.get("meaning_zh") or f.get("meaning"), 80) for f in open_high[:limit]]
    if len(open_high) > limit:
        lines.append(f"另有 {len(open_high) - limit} 個高嚴重度旗標（看食物卡的旗標）")
    return lines


def _missing_lines(holds: list, limit: int = 4) -> list:
    """What the held parts still need, as the components state it (missing_zh), counted per kind."""
    counts = {}
    for part in holds:
        text = sanitize_text(part.get("missing_zh") or part.get("missing_test"), 120)
        if text:
            counts[text] = counts.get(text, 0) + 1
    lines = [f"缺：{text}（{n} 個成分）" for text, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]
    if len(counts) > limit:
        lines.append(f"另有 {len(counts) - limit} 種缺的測試（看食物卡）")
    return lines


def _arms_line(tasting: dict) -> str:
    """'N 4 次（評分 4）、G 4 次（評分 4，食物組）' for a tasting's arms."""
    return "、".join(f"{sanitize_text(a['id'], 40)} {a['runs']} 次（評分 {a['graded_runs']}" + ("，食物組）" if a["food_arm"] else "）")
                    for a in tasting.get("arms") or [])


def _tasting_note(tasting: dict) -> str:
    records = tasting.get("records") or {}
    return (f"試吃 {sanitize_text(tasting.get('date'), 10)}：{_arms_line(tasting)}；紀錄 "
            f"{sanitize_text(records.get('branch'), 40)}:{sanitize_text(records.get('path'), 160)}@{sanitize_text(records.get('commit'), 40)[:7]}")


def _unit_line(unit: dict) -> str:
    commits = "、".join(sanitize_text(c, 40)[:7] for c in unit.get("commits") or [])
    tests = "、".join(sanitize_text(t, 80) for t in (unit.get("tests") or [])[:3])
    return (f"{sanitize_text(unit.get('id'), 160)}（{unit.get('tier')} 級）：{sanitize_text(unit.get('branch'), 60)} {commits}"
            f"；測試 {tests}；依據 {sanitize_text((unit.get('evidence') or {}).get('basis'), 160)}")


def food_pipeline(card: dict) -> dict:
    """Where one food card sits on PIPELINE_STAGES, every stage's state, and its current stage's actions.

    The card's components must already carry `in_current_build`. Planned stages are never the current stage
    and never carry an action: until they are automated a food is shown passing them (┄). A passed stage with
    planned steps is `partial` (◐), never `done`. The test stage is drawn ┄ until a tasting (or consented live
    evidence) is recorded.

    `waiting_on` says who the food waits on (PIPELINE_WAITING_ZH; D28: the agent unless only the owner can move
    it) and `blocker` explains it from the card's own data: where it stops (`where_zh`), the rule or decision
    behind it (`basis_zh`), what happens if nobody acts (`if_ignored_zh`) and what the records cannot say
    (`unknown_zh`). `stage_notes_zh` carries what a recorded tasting or absorption says at its stage.
    """
    fid = card["id"]
    verdict = card.get("verdict") or {}
    headline = verdict.get("headline")
    reasons = [sanitize_text(r, 160) for r in verdict.get("reasons_zh") or verdict.get("reasons") or []]
    parts = [c for c in card.get("components") or [] if isinstance(c, dict)]
    history = [c for r in card.get("historical") or [] for c in r.get("components") or [] if isinstance(c, dict)]
    in_build = [c for c in parts if c.get("in_current_build")]
    open_parts = [c for c in parts if can_absorb(c)]
    # A proposal a D21 absorption record already settled (absorbed, declined or held) is not open any more.
    open_history = [c for c in history if c.get("disposition") == "absorb" and not c.get("decision") and not c.get("d21")]
    restored_away = [c for c in parts if c.get("decision") == "absorbed" and not c.get("in_current_build")]
    removed = [c for c in parts if c.get("decision") == "removed" and not c.get("in_current_build") and not can_absorb(c)]
    readded = [c for c in in_build if c.get("decision") == "removed"]
    backlog = [c for c in history if c.get("decision")]
    holds = [c for c in parts if c.get("disposition") == "hold" and not c.get("decision")]
    ab_holds = [c for c in holds if c.get("missing_code") == "ab"]
    tasting = card.get("tasting") if isinstance(card.get("tasting"), dict) else None
    absorption = card.get("absorption") if isinstance(card.get("absorption"), dict) else None
    rebuilt = [u for u in (absorption or {}).get("units") or [] if u.get("outcome") == "absorbed"]
    states = {s["id"]: "planned" if s["automation"] == "planned" else "todo" for s in PIPELINE_STAGES}
    states["test"] = "planned"  # ┄ until a tasting or consented live evidence says it ran
    if verdict.get("level") == "measured":
        states["test"] = "done"  # a consented live record is test evidence; nothing in v0 produces one yet
    notes = {}
    if tasting:
        states["test"] = "blocked" if tasting["verdict"] == "no-verdict" else "done"
        notes["test"] = _tasting_note(tasting)
        if tasting["verdict"] != "no-verdict":
            notes["sort"] = f"試吃判定：{TASTING_VERDICTS[tasting['verdict']]}（{sanitize_text(tasting.get('verdict_zh'), 200)}）"

    def reach(stage, state, *, skip_planned=False):
        for sid in PIPELINE_ORDER[:PIPELINE_ORDER.index(stage)]:
            if states[sid] == "todo":
                states[sid] = "partial" if sid in PARTIAL_STAGES else "done"
            elif states[sid] == "planned" and skip_planned:
                states[sid] = "skipped"
        states[stage] = state
        return stage

    parity_zh = "和單吃食物比：" + ("實測" if headline == "nutritious" else "未測")
    bad = headline in ("toxic", "risky", "regressed", "diarrhea")
    verdict_zh = VERDICTS[headline][3] if headline in VERDICTS else sanitize_text(headline, 20)
    wanted = []  # (action id, label or None, params or None)
    unknown = []
    if in_build:
        stage = reach("build", "blocked" if bad else "current")
        note = f"在目前版本中（{len(in_build)} 個成分）" + (f"，但判定是「{verdict_zh}」：建議移除" if bad else "")
        if readded:
            note += f"；{len(readded)} 個是移除後又被還原回來的：要重新測試（D6），Claude 會重新試吃（免費）"
        wanted.append(("remove-food", None, {"name": fid, "food": True}))
        if headline == "risky":
            wanted.append(("triage", None, None))
        if readded:
            wanted.append(("taste", "重新試吃（免費）", None))
        if (open_parts or open_history) and not bad:
            wanted.append(("absorb", "吸收其他成分…", None))
        if bad:
            # Removing a skill is a tier-C question (D21): only the owner removes it.
            waiting, where = "owner", f"版本：在目前版本中，但判定是「{verdict_zh}」：移除要你決定"
            basis = reasons + _flag_lines(card) + [BLOCKER_BASIS_ZH["D6"], BLOCKER_BASIS_ZH["D28-owner"]]
            ignored = "這些成分會留在目前版本裡：系統不會自己移除（D7）"
        elif readded:
            waiting, where = "agent", f"版本：{len(readded)} 個成分是移除後又被還原回來的：Claude 會重新試吃（免費）"
            basis, ignored = [BLOCKER_BASIS_ZH["D6"]], "它們留在目前版本，但在重新試吃之前一律當成未測"
            unknown.append(AGENT_WHEN_ZH)
        else:
            waiting = "optional" if open_parts or open_history else "none"
            where = f"沒有卡點：在目前版本中（{len(in_build)} 個成分）" + ("；還有成分可以吸收（可選）" if waiting == "optional" else "")
            basis = [BLOCKER_BASIS_ZH["D6"]] + ([BLOCKER_BASIS_ZH["D11"]] if waiting == "optional" else [])
            ignored = "什麼都不會變：它留在目前版本" + ("，其他成分留在核准" if waiting == "optional" else "")
    elif not card.get("tasted"):
        error = card.get("last_error") if isinstance(card.get("last_error"), dict) else None
        if error:
            stage = reach("quarantine", "blocked")
            failure = sanitize_text(error.get("error_zh") or error.get("error"), 160)
            note = "試吃失敗：" + failure + "；Claude 會查原因再試，或記下不收的理由"
            wanted += [("taste", "再送去試吃", None), ("forget", None, None)]
            waiting, where = "agent", "封存：試吃失敗（" + failure + "）"
            basis = [BLOCKER_BASIS_ZH["D7"], BLOCKER_BASIS_ZH["D28-owner"]]
            ignored = "Claude 接手（D28）；在那之前這樣食物停在封存：不會被檢查，也不會被吸收"
            unknown.append(AGENT_WHEN_ZH)
        elif card.get("tastings") or absorption:
            stage = reach("intake", "current")
            note = "已有 Claude 的試吃紀錄，但還沒跑免費靜態檢查：Claude 會送去試吃（免費）"
            wanted += [("taste", None, None), ("forget", None, None)]
            waiting, where = "agent", "入口：已有試吃紀錄，免費靜態檢查還沒跑"
            basis, ignored = [BLOCKER_BASIS_ZH["D4"], BLOCKER_BASIS_ZH["D25"]], "Claude 接手（D28）；在那之前它停在入口"
            unknown.append(AGENT_WHEN_ZH)
        else:
            stage = reach("intake", "current")
            reports = len(card.get("historical") or [])
            note = "等你送去試吃" + (f"（已匯入 {reports} 份歷史證據，不計入判定）" if reports else "")
            wanted += [("taste", None, None), ("forget", None, None)]
            waiting, where = "owner", "入口：還沒送去試吃"
            basis = [BLOCKER_BASIS_ZH["D4"]] + ([BLOCKER_BASIS_ZH["import"]] if card.get("origin") == "import" else [])
            ignored = "它一直停在入口：不封存、不檢查，也不會被吸收"
            if card.get("origin") != "import":
                unknown.append("紀錄沒有寫當初為什麼沒有試吃（例如用 --no-taste 只登記）")
    elif absorption:
        # D21: the units were rebuilt as OAW code with tests on the working branch; the release decides them all at once.
        settled = f"排掉 {absorption.get('declined', 0)} 個、暫留 {absorption.get('held', 0)} 個"
        owner = sanitize_text(absorption.get("blocked_on_owner"), 300) if absorption.get("blocked_on_owner") else ""
        branches = "、".join(sanitize_text(b, 60) for b in absorption.get("branches") or [])
        if rebuilt:
            stage = reach("build", "current")
            pending = [u for u in rebuilt if u.get("release") != "released"]
            note = f"已吸收 {len(rebuilt)} 個單位（D21：在 {branches} 重建成 OAW 程式和測試）；{settled}"
            notes["approve"] = f"D21 吸收：{len(rebuilt)} 個單位（" + "、".join(f"{sanitize_text(u['id'], 80)} {u['tier']} 級" for u in rebuilt[:4]) + "）"
            notes["build"] = (f"{len(pending)} 個單位等發布（{branches}）" if pending else f"已發布 {len(rebuilt)} 個單位")
            basis = [BLOCKER_BASIS_ZH["D21"]] + [_unit_line(u) for u in rebuilt[:4]]
            if len(rebuilt) > 4:
                basis.append(f"另有 {len(rebuilt) - 4} 個吸收的單位（看食物卡）")
            if owner:
                waiting, where = "owner", "版本：等你決定：" + owner
                basis.append(BLOCKER_BASIS_ZH["D28-owner"])
                ignored = "這個決定之前，相關的單位停在原地；已重建的單位照常等發布"
            elif pending:
                waiting, where = "release", f"版本：{len(pending)} 個單位已在 {branches} 重建，等發布（合併 PR 時一次決定）"
                basis.append(BLOCKER_BASIS_ZH["release"])
                ignored = f"這些單位留在 {branches}，不會進正式版本；其他食物不受影響"
            else:
                waiting, where = "none", f"沒有卡點：已發布 {len(rebuilt)} 個單位"
                basis.append(BLOCKER_BASIS_ZH["release"])
                ignored = "什麼都不會變：它們已經在正式版本裡"
        else:
            stage = reach("sort", "done")
            states["approve"] = states["build"] = "skipped"
            wanted.append(("forget", None, None))
            note = f"沒有吸收任何單位（D21）：{settled}"
            basis = [BLOCKER_BASIS_ZH["D21"]]
            if owner:
                waiting, where = "owner", "分流：等你決定：" + owner
                basis.append(BLOCKER_BASIS_ZH["D28-owner"])
                ignored = "暫留的單位停在原地，直到你決定"
            else:
                waiting, where = "none", f"沒有卡點：沒有吸收任何單位（{settled}）"
                ignored = "什麼都不會變；暫留的單位等它們的前置條件"
    elif headline == "toxic":
        stage = reach("sort", "blocked", skip_planned=True)
        note = "你確認有毒：整樣排掉，不會進專案"
        wanted.append(("forget", None, None))
        waiting, where = "none", "沒有卡點：你確認有毒，整樣排掉"
        basis, ignored = reasons + [BLOCKER_BASIS_ZH["toxic"]], "不會進專案；「忘掉這樣食物」可以把它從食物卡拿掉（可選）"
    elif tasting and not (restored_away or removed):
        # An owner's removal or restore of copied parts (D6, D14) stands over an older tasting.
        label = TASTING_VERDICTS[tasting["verdict"]]
        said = sanitize_text(tasting.get("verdict_zh"), 200)
        owner = sanitize_text(tasting.get("blocked_on_owner"), 300) if tasting.get("blocked_on_owner") else ""
        basis = [BLOCKER_BASIS_ZH["D25"], _tasting_note(tasting)]
        if tasting["verdict"] == "no-verdict":
            stage = reach("test", "blocked")
            why = owner or sanitize_text(tasting.get("notes"), 300)
            note = f"試吃沒有判定：{why}" + ("" if owner else "；Claude 會重跑")
            basis = [BLOCKER_BASIS_ZH["D28-verdict"], f"食物組 {sanitize_text(tasting.get('food_arm'), 40)}：評分過的執行 "
                     f"{tasting.get('food_arm_graded_runs', 0)} 次"] + basis[1:]
            if owner:
                waiting, where = "owner", "實測：試吃沒有判定，等你：" + owner
                basis.append(BLOCKER_BASIS_ZH["D28-owner"])
                ignored = "這樣食物停在實測：食物組沒跑完就沒有判定（D28）；其他食物不受影響"
            else:
                waiting, where = "agent", "實測：試吃沒有判定（" + why + "）；Claude 會重跑"
                ignored = "Claude 接手重跑（D28）；在那之前沒有判定，也不會被吸收"
                unknown.append(AGENT_WHEN_ZH)
            wanted.append(("forget", None, None))
        elif tasting["verdict"] in ("absorb", "plug-in"):
            stage = reach("approve", "current")
            if tasting["verdict"] == "absorb":
                note = f"試吃判定：{label}（{said}）；下一步：Claude 依 D21 把挑中的單位重建成 OAW 程式和測試，記成吸收紀錄；你在發布時合併"
                where = "核准：試吃判定吸收；Claude 依 D21 重建成 OAW 程式和測試"
                basis.insert(1, BLOCKER_BASIS_ZH["D21"])
            else:
                note = f"試吃判定：{label}（{said}）；下一步：Claude 接上官方版（連接器），不吸收食物的程式"
                where = "核准：試吃判定插上；Claude 接上官方版"
            if open_parts:
                wanted.append(("absorb", "照原樣複製吸收（可選）…", None))
            wanted.append(("forget", None, None))
            if owner:
                waiting, where = "owner", where + "；等你：" + owner
                basis.append(BLOCKER_BASIS_ZH["D28-owner"])
                ignored = "這個決定之前，這樣食物停在核准"
            else:
                waiting = "agent"
                ignored = "Claude 接手（D28）；完成後停在版本，等發布"
                unknown.append(AGENT_WHEN_ZH)
        elif tasting["verdict"] == "optional" and owner:
            # D29 + D21: optional, but making it available needs a tier-C decision (food code, a runtime dependency).
            stage = reach("approve", "current")
            note = f"試吃判定：{label}（{said}）；要裝成可選用之前，等你：{owner}"
            wanted.append(("forget", None, None))
            waiting, where = "owner", "核准：試吃判定可選用；等你：" + owner
            basis.insert(1, BLOCKER_BASIS_ZH["D29"])
            basis.append(BLOCKER_BASIS_ZH["D28-owner"])
            ignored = "不會設為預設；在你決定之前，它不會被裝進來"
        else:
            stage = reach("sort", "done")
            states["approve"] = states["build"] = "skipped"
            if tasting["verdict"] == "optional":
                note = f"試吃判定：{label}（{said}）；不設為預設，要用時才叫"
                where = f"沒有卡點：試吃判定{label}"
                basis.insert(1, BLOCKER_BASIS_ZH["D29"])
                ignored = "不設為預設；要用時才叫（D29）"
            else:
                note = f"試吃判定：{label}（{said}）"
                where = f"沒有卡點：試吃判定{label}"
                ignored = "不會被吸收；「忘掉這樣食物」可以把它從食物卡拿掉（可選）"
            wanted.append(("forget", None, None))
            waiting = "none"
    elif headline == "risky":
        open_high = (card.get("flags") or {}).get("open_high") or 0
        if open_high:
            # D28: the flags inform the rebuild and the goldfish review; they do not park the food on the owner.
            stage = reach("static", "current")
            note = f"{open_high} 個高嚴重度旗標：只供參考，不擋這樣食物；下一步：Claude 在試吃區試吃（D25、D28）"
            wanted += [("triage", "分流旗標（可選，終端確認碼）", None), ("forget", None, None)]
            waiting, where = "agent", f"靜態：{open_high} 個高嚴重度旗標（只供參考）；下一步：Claude 在試吃區試吃"
            basis = [BLOCKER_BASIS_ZH["D28-static"]] + _flag_lines(card)
            ignored = "Claude 接手試吃（D28）；帶旗標的成分在你分流之前不能照原樣複製，重建成 OAW 程式不受影響"
            unknown.append(AGENT_WHEN_ZH)
        else:
            stage = reach("static", "blocked")
            note = "你擋下了這樣食物：" + sanitize_text("；".join(str(r) for r in verdict.get("reasons") or []), 120)
            wanted += [("triage", None, None), ("forget", None, None)]
            waiting, where = "none", "沒有卡點：你擋下了這樣食物"
            basis, ignored = reasons, "它停在靜態，不會被吸收"
    elif verdict.get("stale"):
        stage = reach("static", "current")
        note = "掃描規則更新了：Claude 會用新規則再試吃（免費），之後才能吸收"
        wanted += [("taste", "用新規則再試吃（免費）", None), ("forget", None, None)]
        waiting, where = "agent", "靜態：掃描規則更新了，Claude 會用新規則再試吃"
        basis, ignored = [BLOCKER_BASIS_ZH["rescan"]], "判定停在舊規則的結果：成分一律暫留，不能吸收"
        unknown.append(AGENT_WHEN_ZH)
    elif headline in ("inedible", "regressed", "diarrhea"):
        stage = reach("sort", "blocked", skip_planned=headline == "inedible")
        note = {"inedible": "OAW 照原樣沒辦法消化（不是說它有害）", "regressed": "實測變差：不吸收",
                "diarrhea": "拉肚子：會傷到現有配方"}[headline]
        wanted.append(("forget", None, None))
        waiting, where = "none", "沒有卡點：" + note
        basis, ignored = reasons, "不會被吸收；「忘掉這樣食物」可以把它從食物卡拿掉（可選）"
    elif open_parts:
        stage = reach("approve", "current")
        note = (f"可以吸收：{len(open_parts)} 個成分；Claude 依 D21 重建成 OAW 程式和測試，你在發布時合併（照原樣複製吸收是可選的）"
                + (f"；{len(open_history)} 個歷史提案可以記成待辦（可選）" if open_history else ""))
        wanted += [("absorb", "照原樣複製吸收（可選）…", None), ("forget", None, None)]
        waiting = "agent"
        where = f"核准：{len(open_parts)} 個成分可以吸收；Claude 依 D21 重建成 OAW 程式和測試"
        basis = [BLOCKER_BASIS_ZH["D21"], BLOCKER_BASIS_ZH["D11"]] + ([BLOCKER_BASIS_ZH["backlog"]] if open_history else [])
        ignored = "Claude 接手重建（D28）；照原樣複製吸收（「照原樣複製吸收（可選）…」）是可選的舊流程"
        unknown.append(AGENT_WHEN_ZH)
    elif open_history:
        # Imported proposals are backlog the owner may note; nothing waits on that choice (D28).
        stage = reach("approve", "current")
        paper = card.get("kind") == "paper"
        note = (f"可選：{len(open_history)} 個歷史提案可以記成待辦" +
                ("（論文的想法要重新實作成 OAW 程式和測試，不複製原文；D5、D21）" if paper else ""))
        wanted += [("absorb", "記成待辦（可選）…", None), ("forget", None, None)]
        waiting = "optional"
        where = f"沒有卡點：{len(open_history)} 個歷史提案可以記成待辦（可選）"
        basis = ([BLOCKER_BASIS_ZH["paper"]] if paper else []) + [BLOCKER_BASIS_ZH["backlog"], BLOCKER_BASIS_ZH["D21"]]
        ignored = "什麼都不會變：提案留在食物卡；要吸收，Claude 依 D21 重建成 OAW 程式和測試，記成吸收紀錄"
    elif restored_away:
        stage = reach("build", "current")
        builds = [d.get("build") for d in card.get("decisions") or [] if d.get("kind") == "absorb" and d.get("build")]
        note = "已還原掉：吸收的成分不在目前版本"
        if builds:
            wanted.append(("restore", f"還原到這版（{sanitize_text(builds[-1], 40)}）", {"build": builds[-1]}))
        wanted.append(("forget", None, None))
        waiting, where = "optional", "沒有卡點：吸收的成分被還原掉了，不在目前版本"
        basis, ignored = [BLOCKER_BASIS_ZH["D14"]], "目前版本不變；想要回來就按「還原到這版」"
    elif removed:
        stage = reach("build", "removed")
        note = "已移除：要再加回，先重新送去試吃（免費），再核准（D6）"
        wanted += [("taste", "再送去試吃（免費）", None), ("forget", None, None)]
        waiting, where = "optional", "沒有卡點：你移除了它"
        basis, ignored = [BLOCKER_BASIS_ZH["D6"]], "它不會自己加回；要加回，先重新送去試吃（免費），再核准"
    elif backlog:
        stage = reach("approve", "done")
        states["build"] = "skipped"
        note = f"已記成待辦 {len(backlog)} 項（未改程式，沒有新版本）"
        wanted.append(("forget", None, None))
        waiting, where = "none", f"沒有卡點：已記成待辦 {len(backlog)} 項（未改程式）"
        basis = [BLOCKER_BASIS_ZH["backlog"]] + ([BLOCKER_BASIS_ZH["paper"]] if card.get("kind") == "paper" else [])
        ignored = "待辦留在決定紀錄裡；要實作成 OAW 程式和測試，才會進版本"
    elif card.get("kind") == "paper" and not parts and not history:
        # Splitting a paper into units needs a model: Claude does it as the Elephant (D28); the engine invents nothing.
        stage = reach("static", "current")
        note = "論文已封存（固定 arXiv 版本＋sha256）；下一步：Claude 當 Elephant 拆單位，匯入紀錄（計畫：匯入紀錄），或直接記錄試吃／吸收"
        wanted.append(("forget", None, None))
        waiting, where = "agent", "靜態：論文的單位還沒拆；Claude 接手"
        basis = [BLOCKER_BASIS_ZH["paper"]]
        ignored = "Claude 接手拆單位（D28）；在那之前論文停在靜態"
        unknown.append(AGENT_WHEN_ZH)
    else:
        stage = reach("sort", "current")
        if holds:
            note = (f"暫留 {len(holds)} 個成分" + (f"（{len(ab_holds)} 個 skill 文字缺行為 A/B，D17）" if ab_holds else "")
                    + "：下一步 Claude 在試吃區試吃（D25、D28）")
            flagged = [c for c in holds if c.get("missing_code") in OWNER_MISSING]
            waiting = "agent"
            where = f"分流：暫留 {len(holds)} 個成分；下一步：Claude 在試吃區試吃"
            basis = ([BLOCKER_BASIS_ZH["D17"]] if ab_holds else []) + _missing_lines(holds) + [BLOCKER_BASIS_ZH["D25"], parity_zh + "（D16）"]
            ignored = ("Claude 接手試吃（D28）：試吃之後才有判定；在那之前成分暫留，不會被吸收" +
                       (f"；{len(flagged)} 個成分帶未分流的旗標，可以在終端分流（可選）：catalog.py menu → 12" if flagged else ""))
            unknown.append(AGENT_WHEN_ZH)
        else:
            note = "沒有可以吸收的成分"
            waiting, where = "none", "沒有卡點：沒有可以吸收的成分"
            basis, ignored = [BLOCKER_BASIS_ZH["D5"]], "它停在分流；「忘掉這樣食物」可以把它從食物卡拿掉（可選）"
        note += "；" + parity_zh
        wanted.append(("forget", None, None))
    actions = []
    for aid, label, params in wanted:
        spec = PIPELINE_ACTIONS[aid]
        actions.append({"id": aid, "stage": stage, "endpoint": spec["endpoint"], "where": spec["where"],
                        "label_zh": label or spec["label_zh"], "params": params or {"food": fid}})
    label_zh = next(s["label_zh"] for s in PIPELINE_STAGES if s["id"] == stage)
    parity = headline == "nutritious"  # derive() gives nutritious only with a measured parity floor
    # 看計畫 sits on the 計畫 cell only once the food has passed it; before that the plan is in the food card.
    plan_reached = states["plan"] in ("done", "partial")
    return {"stage": stage, "stage_label_zh": label_zh, "state": states[stage], "state_zh": PIPELINE_STATES[states[stage]][1],
            "stages": states, "note_zh": note, "actions": actions, "ab_holds": len(ab_holds), "readded_untested": len(readded),
            "details": [{"stage": "plan", "id": "plan", "label_zh": "看計畫"}] if card.get("tasted") and card.get("plan") and plan_reached else [],
            "stage_notes_zh": {sid: notes[sid] for sid in PIPELINE_ORDER if sid in notes},
            "parity": {"state": "measured" if parity else "not-tested",
                       "label": "parity vs food alone: " + ("measured" if parity else "not tested"),
                       "label_zh": "和單吃食物比（齊平底線）：" + ("實測" if parity else "未測")},
            "waiting_on": waiting, "waiting_zh": PIPELINE_WAITING_ZH[waiting],
            "blocker": {"where_zh": where, "basis_zh": [b for b in basis if b] or ["紀錄裡沒有寫依據"],
                        "if_ignored_zh": ignored, "unknown_zh": unknown}}


def pipeline_table() -> dict:
    """The stage table, inlets and display vocabulary, as written into view.json."""
    return {"stages": copy_json(PIPELINE_STAGES), "inlets": copy_json(PIPELINE_INLETS), "order": list(PIPELINE_ORDER),
            "automation_zh": dict(PIPELINE_AUTOMATION), "symbols": {k: v[0] for k, v in PIPELINE_STATES.items()},
            # view.json is written with sorted keys, so the display order travels as lists.
            "legend": list(PIPELINE_STATES), "automation_order": list(PIPELINE_AUTOMATION),
            "states_zh": {k: v[1] for k, v in PIPELINE_STATES.items()}, "actions": copy_json(PIPELINE_ACTIONS),
            "live_stages": dict(LIVE_STAGES), "empty_zh": PIPELINE_EMPTY_ZH,
            "waiting_zh": dict(PIPELINE_WAITING_ZH), "waiting_order": list(PIPELINE_WAITING_ZH),
            "tasting_verdicts_zh": dict(TASTING_VERDICTS), "tiers_zh": dict(TIERS)}


def copy_json(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def food_card(entry: dict, evidence: list, decisions: list, plan: dict | None = None) -> dict:
    derived = derive(evidence, decisions)
    backlog = {cid for d in decisions if d.get("kind") == "absorb" and d.get("outcome") == "backlog" for cid in d.get("components") or []}
    records = food_records(evidence, entry["id"])
    absorption = absorption_summary(records["absorptions"])
    # A unit a D21 absorption record settled, by every id it may carry (a component id or an imported hist: id).
    settled = {alias: {"outcome": u["outcome"], "branch": u["branch"], "tier": u.get("tier")}
               for u in (absorption or {}).get("units", []) for alias in unit_aliases(u["id"])}
    historical = []
    for record in evidence:
        if evidence_class(record) == "historical":
            summary = historical_summary(record)
            summary["components"] = [{**c, "decision": "absorbed as backlog item" if c.get("id") in backlog else None,
                                      "d21": settled.get(c.get("id"))}
                                     for c in summary["components"]]
            historical.append(summary)
    static = [r for r in evidence if evidence_class(r) == "static"]
    s = max(static, key=lambda r: (int(r.get("scanner_version") or 0), str(r.get("recorded_at") or ""))) if static else None
    counts = {k: sum(1 for c in derived["components"] if c["disposition"] == k) for k in DISPOSITIONS}
    source = entry.get("source", {})
    private = is_local_source(source)
    kind = "paper" if source.get("kind") == "paper" else "repo"
    display = sanitize_text(entry.get("display") or entry.get("id"), 80)
    facts = s.get("paper") if s and s.get("food_kind") == "paper" and isinstance(s.get("paper"), dict) else None
    paper = None
    if kind == "paper":
        # The sealed taste speaks first; before a taste, an imported record's own description is shown as such.
        imported = next((r["paper"] for r in historical if isinstance(r.get("paper"), dict)), None)
        paper = ({**facts, "from": "static"} if facts else {**imported, "from": "imported"} if imported else None)
    safety_text = ("owner-confirmed toxic" if derived["safety"] == "toxic" else
                   f"paper: PDF sealed ({facts['pdf_bytes']} bytes, sha256 {str(facts['pdf_sha256'])[:12]}), never parsed or executed"
                   if facts and derived["safety"] != "flagged" else
                   f"no toxic signal observed ({s['counts']['files']} files, {len(s['checks_run'])} checks, {s['tree_sha256'][:12]})" if s and derived["safety"] != "flagged" else
                   f"{derived['flags']['open']} open flag(s), {derived['flags']['open_high']} high" if s else "not checked")
    food_decisions = [{"at": d.get("at"), "kind": d.get("kind"), "components": d.get("components") or [], "outcome": d.get("outcome"),
                       "reason": sanitize_text(d.get("reason", ""), 160), "build": d.get("build")} for d in decisions]
    triaged = {d["flag"]: d["outcome"] for d in decisions if _valid_decision(d) and d["kind"] == "triage"}
    severity_rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    flags = [{"id": sanitize_text(f.get("id"), 300), "rule": sanitize_text(f.get("rule"), 20), "path": sanitize_text(f.get("path"), 200),
              "line": f.get("line") if isinstance(f.get("line"), int) else None, "severity": f.get("severity") if f.get("severity") in severity_rank else "low",
              "meaning": sanitize_text(f.get("meaning"), 120), "meaning_zh": FLAG_MEANINGS_ZH.get(f.get("rule")),
              "allergen": sanitize_text(f.get("allergen"), 40) or None,
              "triage": triaged.get(f.get("id"))}
             for f in sorted((s or {}).get("flags", []), key=lambda f: (severity_rank.get(f.get("severity"), 4), str(f.get("id"))))
             if isinstance(f, dict)][:80]
    error = entry.get("last_error") if isinstance(entry.get("last_error"), dict) else None
    return {"id": entry["id"], "display": display, "repo": None if private else source.get("url"), "origin": entry.get("origin"),
            "lifecycle": entry.get("lifecycle"), "flag_list": flags,
            "last_error": {"at": error.get("at"), "error": sanitize_text(error.get("error"), 300),
                           "error_zh": sanitize_text(error.get("error_zh"), 300)} if error else None,
            "pinned": {"commit": source.get("commit"), "commit7": (source.get("commit") or "")[:7] or None,
                       "integrity": source.get("integrity"), "tree_sha12": (s or {}).get("tree_sha256", "")[:12] or None,
                       # A paper is pinned to an arXiv version plus the sha256 of its sealed PDF, not to a commit.
                       "version": (facts or {}).get("version"), "pdf_sha12": str((facts or {}).get("pdf_sha256") or "")[:12] or None},
            "tasted": bool(s), "kind": kind, "paper": paper,
            "components_note_zh": PAPER_COMPONENTS_NOTE_ZH if kind == "paper" and not derived["components"] else None,
            "verdict": {k: derived[k] for k in ("headline", "symbol", "ascii", "label", "label_zh", "reasons", "reasons_zh", "chips", "badges",
                                                "level", "stale")},
            "safety_text": safety_text, "exec_class": derived["exec_class"], "allergens": derived["allergens"],
            "flags": derived["flags"], "license": (s or {}).get("license", {}).get("spdx") if s else None,
            "components": [{**c, "d21": settled.get(c["id"])} for c in derived["components"]], "counts": counts,
            "historical": historical,
            "plan": {"status": plan["status"], "plan_id": plan["plan_id"], "estimate": plan["estimate"]} if plan else None,
            "decisions": food_decisions,
            # D25/D28: Claude's tastings (oldest first; the latest decides) and D21 absorptions; records the engine
            # refuses are listed with why, never counted.
            "tastings": [tasting_summary(t) for t in records["tastings"]],
            "tasting": tasting_summary(records["tastings"][-1]) if records["tastings"] else None,
            "absorption": absorption, "records_refused": records["refused"]}


def food_source_zh(card: dict) -> str:
    """Where a food comes from and what it is pinned to: a repository's commit, a paper's arXiv version plus sha256."""
    pinned = card.get("pinned") or {}
    if card.get("kind") == "paper":
        paper = card.get("paper") or {}
        arxiv = sanitize_text(paper.get("arxiv_id"), 40)
        version = sanitize_text(pinned.get("version") or paper.get("version"), 8)
        sha = sanitize_text(pinned.get("pdf_sha12"), 12)
        where = f"arXiv:{arxiv}" if arxiv else "本機 PDF"
        if sha:
            return where + (f" {version}" if version else "") + f" · sha256 {sha}"
        # Before the taste only the record's own version is known; nothing is pinned yet.
        return where + (f"（紀錄寫的版本 {version}）" if version else "") + " · 還沒封存（未固定版本）"
    url = sanitize_text(card.get("repo"), 200) or "本機 repo（路徑不公開）"
    commit = sanitize_text(pinned.get("commit7"), 12)
    return url + (f" @ {commit}" if commit else " · 還沒封存（未固定版本）")


def question_brief(card: dict, question: dict) -> str:
    """The owner's question with the food's facts from view.json, as text to paste into a Claude conversation."""
    pipeline = card.get("pipeline") or {}
    blocker = pipeline.get("blocker") or {}
    counts = card.get("counts") or {}
    stage = next((s for s in PIPELINE_STAGES if s["id"] == question.get("stage")), None)
    lines = [f"關於 OAW 消化道的問題（{sanitize_text(question.get('time'), 30)}，問題編號 {sanitize_text(question.get('id'), 20)}）",
             f"食物：{sanitize_text(card.get('display'), 80)}（{sanitize_text(card.get('id'), 64)}，{'論文' if card.get('kind') == 'paper' else 'repo'}）",
             "來源：" + food_source_zh(card),
             f"問的時候在：{stage['label_zh'] if stage else sanitize_text(question.get('stage'), 20)}"
             f"（現在：{sanitize_text(pipeline.get('stage_label_zh'), 8)} · {sanitize_text(pipeline.get('state_zh'), 8)}"
             f" · {sanitize_text(pipeline.get('waiting_zh'), 30)}）",
             "說明：" + sanitize_text(pipeline.get("note_zh"), 300),
             "卡在哪：" + (sanitize_text(blocker.get("where_zh"), 200) or "紀錄裡沒有寫"),
             "依據：" + ("；".join(sanitize_text(b, 200) for b in blocker.get("basis_zh") or []) or "紀錄裡沒有寫"),
             "你不處理會怎樣：" + (sanitize_text(blocker.get("if_ignored_zh"), 200) or "紀錄裡沒有寫")]
    if blocker.get("unknown_zh"):
        lines.append("紀錄沒寫的：" + "；".join(sanitize_text(u, 200) for u in blocker["unknown_zh"]))
    verdict = card.get("verdict") or {}
    level = verdict.get("level")
    lines.append(f"成分：吸收 {counts.get('absorb', 0)}、暫留 {counts.get('hold', 0)}、排掉 {counts.get('excrete', 0)}"
                 f" · 判定 {sanitize_text(verdict.get('label_zh'), 20)}（{EVIDENCE_LEVELS_ZH.get(level) or sanitize_text(level, 30)}）")
    proposals = [c for r in card.get("historical") or [] for c in r.get("components") or [] if isinstance(c, dict)]
    if proposals:
        tally = {k: sum(1 for c in proposals if c.get("disposition") == k) for k in DISPOSITIONS}
        lines.append(f"匯入紀錄的提案（歷史證據，不計入判定）：吸收 {tally['absorb']}、暫留 {tally['hold']}、排掉 {tally['excrete']}")
    lines.append("問題：" + sanitize_text(question.get("question"), 1000))
    return "\n".join(lines)


def place_card(card: dict, receipt) -> dict:
    """Mark which parts the current layer holds (from the absorb receipt), then put the card on the pipeline."""
    # Only installed parts are in a build; a backlog note changes no code.
    present = {cid for cid, part in ((receipt or {}).get("components") or {}).items()
               if isinstance(part, dict) and part.get("outcome") == "installed"}
    for part in card["components"]:
        part["in_current_build"] = part["id"] in present
        part["can_absorb"] = can_absorb(part)
    for report in card["historical"]:
        for part in report["components"]:
            part["in_current_build"] = False
    card["pipeline"] = food_pipeline(card)
    return card


def build_view(state: dict) -> dict:
    """The only view model renderers read. Derived, never hand-edited."""
    registry = state.get("registry") or {"foods": {}}
    evidence = state.get("evidence") or {}
    decisions = state.get("decisions") or []
    plans = state.get("plans") or {}
    builds = state.get("builds") or {"builds": [], "current": None}
    policy = state.get("policy")
    scout = state.get("scout") or {"candidates": {}}
    receipts = state.get("receipts") or {}
    foods = []
    for fid, entry in sorted(registry.get("foods", {}).items()):
        mine = decisions_for(decisions, fid)
        foods.append(place_card(food_card(entry, evidence.get(fid, []), mine, plans.get(fid)), receipts.get(fid)))
    candidates = sorted(scout.get("candidates", {}).values(), key=lambda c: (-int(c.get("stars") or 0), c.get("key", "")))
    timeline = [{"n": b.get("n"), "name": b.get("name"), "label": sanitize_text(b.get("label", ""), 160),
                 "label_zh": sanitize_text(b.get("label_zh", ""), 160) or None, "kind": b.get("kind"),
                 "created_at": b.get("created_at"), "skills": b.get("skills", []), "components": b.get("components", []),
                 "change": b.get("change", {}), "effect": b.get("effect"), "doctor": b.get("doctor"),
                 "current": b.get("name") == builds.get("current"), "restore": f"catalog.py restore {b.get('name')}"}
                for b in builds.get("builds", [])]
    backlog = {(f["id"], cid) for f in foods for d in f["decisions"] if d["kind"] == "absorb" and d["outcome"] == "backlog"
               for cid in d["components"]}
    installed = sum(1 for f in foods for c in f["components"] if c.get("in_current_build"))
    rebuilt = sum((f.get("absorption") or {}).get("absorbed", 0) for f in foods)
    releasing = [f for f in foods if f["pipeline"]["waiting_on"] == "release"]
    funnel = {"submitted": len(foods), "tasted": sum(1 for f in foods if f["tasted"]),
              "measured": sum(1 for f in foods if f["verdict"]["level"] == "measured"),
              "agent_tasted": sum(1 for f in foods if f.get("tastings")),
              # Installed parts present in the current layer plus units rebuilt under D21 (on the working branch until
              # the release); backlog notes are counted apart and change no code.
              "absorbed_parts": installed + rebuilt, "installed_parts": installed, "rebuilt_units": rebuilt,
              "backlog_items": len(backlog),
              "by_stage": {sid: sum(1 for f in foods if f["pipeline"]["stage"] == sid) for sid in PIPELINE_ORDER},
              "by_waiting": {w: sum(1 for f in foods if f["pipeline"]["waiting_on"] == w) for w in PIPELINE_WAITING_ZH}}
    # D21/D28: the release is one owner decision for the whole branch, never one per food.
    release = {"foods": [f["id"] for f in releasing],
               "units": sum((f.get("absorption") or {}).get("release_pending", 0) for f in releasing),
               "branches": sorted({b for f in releasing for b in (f.get("absorption") or {}).get("branches") or []}),
               "waiting_zh": PIPELINE_WAITING_ZH["release"], "note_zh": BLOCKER_BASIS_ZH["release"]}
    view = {
        "schema": VIEW_SCHEMA, "release": RELEASE,
        "generated_from": {name: record_sha256(state.get(name)) for name in ("registry", "evidence", "decisions", "builds", "policy", "scout", "plans", "effect", "receipts")},
        "vocabulary": {"verdicts": {k: {"symbol": v[0], "ascii": v[1], "label": v[2], "label_zh": v[3]} for k, v in VERDICTS.items()},
                       "dispositions": {k: {"colour": v[0], "label_zh": v[1]} for k, v in DISPOSITIONS.items()},
                       "evidence_levels": EVIDENCE_LEVELS},
        "my_oaw": {"release": RELEASE, "current_build": builds.get("current"),
                   "current_matches_build": state.get("current_matches_build"),
                   "timeline": timeline, "effect": state.get("effect")},
        "feeding": {"add": "catalog.py add URL [URL ...]",
                    "scout": {"order_basis": "queue order only (stars), not quality",
                              "last_run": (scout.get("runs") or [None])[-1],
                              "dropped_without_review": int(scout.get("dropped_total", 0)),
                              "candidates": [{"rank": i + 1, "key": c.get("key"), "display": sanitize_text(c.get("display"), 80),
                                              "description": sanitize_text(c.get("description"), 160), "stars": c.get("stars"),
                                              "relevance": c.get("relevance"), "status": c.get("status", "candidate"),
                                              "weeks_seen": c.get("weeks_seen", [])} for i, c in enumerate(candidates)]}},
        "pipeline": pipeline_table(), "foods": foods, "funnel": funnel, "release_pending": release,
        "policy": {"set": bool(policy), **({k: policy[k] for k in ("per_food_token_cap", "weekly_token_cap", "sandbox", "set_at") if k in policy} if policy else {}),
                   "paid_runs_enabled": False, "note": "v0 shows plans and estimates only; paid runs are not implemented"},
        "honesty": ["No evidence, no verdict; stars only order the scout queue.",
                    "Food bytes stay sealed outside the project and are never executed.",
                    "Static rules raise flags only; toxic needs owner confirmation.",
                    "Imported reports are historical-prior and never counted in a verdict.",
                    "An agent tasting gives a verdict only when its food arm ran and was graded; numbers keep their protocol.",
                    "Quality is 'not measured' unless consented live evidence exists; never 'enhanced' without it.",
                    "While running, only progress and spend are shown, never interim scores."],
    }
    return view
