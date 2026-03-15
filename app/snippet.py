import re
from dataclasses import dataclass
from typing import Iterable, Optional

'''定制化抽片段，因为有些测试不是很准确，所以做了点定制化的东西'''

@dataclass
class CandidateDoc:
    uri: str
    score: float
    content: str


# 中文操作词 → 对应的英文代码关键词，用于在 Python 代码里定位目标片段
_ZH_TO_CODE: dict[str, str] = {
    "创建": "create", "提交": "commit", "上传": "upload",
    "注册": "register", "检索": "find",  "读取": "read",
    "会话": "session",  "记忆": "memory", "资源": "resource",
    "消息": "message",  "路径": "path",   "文件": "file",
    "代理": "agent",    "查询": "query",  "删除": "delete",
}


def _tokens(text: str) -> set[str]:
    en = set(re.findall(r"[A-Za-z][A-Za-z0-9_]{1,}", text.lower()))
    zh = set(re.findall(r"[\u4e00-\u9fff]{2,}", text))
    return en | zh


def _expand(tokens: set[str]) -> set[str]:
    """把中文词扩展成英文代码词，方便在源码里做 token 匹配。"""
    return tokens | {_ZH_TO_CODE[t] for t in tokens if t in _ZH_TO_CODE}


def _match_score(text: str, tokens: set[str]) -> int:
    t = text.lower()
    return sum(1 for tok in tokens if tok in t)


def _is_code_doc(uri: str, content: str) -> bool:
    if uri.lower().endswith(".py"):
        return True
    hits = sum(1 for ln in content.splitlines()[:40]
               if re.match(r"\s*(def |class |import |from [\w.]+ import )", ln))
    return hits >= 2



def _extract_prompt_block(text: str) -> Optional[str]:
    for pat in [
        r'(?ms)^\s*prompt\s*=\s*f?""".*?"""',
        r"(?ms)^\s*prompt\s*=\s*f?'''.*?'''",
        r'(?m)^\s*prompt\s*=\s*.+$',
    ]:
        m = re.search(pat, text)
        if m:
            return m.group(0).strip()
    return None


def _best_fenced_block(content: str, tokens: set[str]) -> Optional[str]:
    blocks = re.findall(r"```[a-zA-Z0-9_+-]*\n(.*?)```", content, flags=re.S)
    if not blocks:
        return None
    ranked = sorted(blocks, key=lambda b: _match_score(b, tokens), reverse=True)
    return ranked[0].strip() if _match_score(ranked[0], tokens) > 0 else None


def _extract_region(content: str, tokens: set[str]) -> Optional[str]:
    lines = content.splitlines()
    if not lines:
        return None

    best = max(range(len(lines)), key=lambda i: _match_score(lines[i], tokens))
    if _match_score(lines[best], tokens) == 0:
        return None

    start = best
    while start > 0:
        prev = lines[start - 1].rstrip()
        if not prev or prev.startswith("#"):
            break
        if prev.endswith((":", "：")):
            start -= 1
            break
        if prev and (prev[0] in (' ', '\t', '"', "'", '(') or prev.startswith("client.")):
            start -= 1
        else:
            break

    end = best + 1
    blanks = 0
    while end < len(lines):
        if lines[end].rstrip():
            blanks = 0
        else:
            blanks += 1
            if blanks >= 2:
                break
        if lines[end].lstrip().startswith("###"):
            break
        end += 1

    return "\n".join(lines[start:end]).strip() or None


def _best_window(content: str, tokens: set[str], before: int = 4, after: int = 16) -> tuple[str, int]:
    lines = content.splitlines()
    if not lines:
        return "", 0

    best = max(range(len(lines)), key=lambda i: _match_score(lines[i], tokens))
    score = _match_score(lines[best], tokens)
    if score == 0:
        return "", 0

    start = max(0, best - before)
    end = min(len(lines), best + after)
    return "\n".join(lines[start:end]).strip(), score


def select_snippet(query: str, docs: Iterable[CandidateDoc]) -> str:
    docs = list(docs)
    if not docs:
        return ""

    tokens = _tokens(query)
    ctokens = _expand(tokens)   # 加入了中文词对应的英文代码词

    if tokens & {"prompt", "提示词", "llm", "大语言模型"}:
        for d in sorted(docs, key=lambda d: d.score, reverse=True):
            block = _extract_prompt_block(d.content)
            if block:
                return block

    def rank_key(d: CandidateDoc) -> float:
        return d.score + _match_score(d.uri, tokens) * 0.5

    ranked = sorted(docs, key=rank_key, reverse=True)

    # 判断是否为代码查询：明确要求代码、有下划线标识符、或 query 里有能翻译成代码词的中文词
    has_code_hint = (
        bool(tokens & {"代码", "代码片段", "code", "python"})
        or re.search(r"[a-z]{3,}_[a-z]{3,}", query) is not None
        or bool(ctokens - tokens)   # 说明有中文词被翻译成了英文代码词
    )
    code_intent = has_code_hint and any(_is_code_doc(d.uri, d.content) for d in ranked[:3])

    if code_intent:
        code_docs = [d for d in ranked if _is_code_doc(d.uri, d.content)] or ranked

        for d in code_docs:
            block = _best_fenced_block(d.content, ctokens)
            if block:
                return block

        for d in code_docs:
            region = _extract_region(d.content, ctokens)
            if region:
                return region

        return code_docs[0].content.strip()

    best_window, best_score, best_full = "", 0, ""
    for d in ranked:
        window, score = _best_window(d.content, ctokens)
        if score > best_score:
            best_window, best_score, best_full = window, score, d.content.strip()

    if best_full:
        return best_full
    if best_window:
        return best_window

    return ranked[0].content.strip() if ranked else ""
