from typing import Dict, Any, List

def _score_from_comments(comments: List[Dict[str,Any]]) -> float:
    if not comments:
        return 0.3
    n = len(comments)
    avg_len = sum(len(c.get("body","")) for c in comments)/max(1,n)
    score = 0.8 if avg_len < 200 else 0.6
    score += min(0.2, 0.02 * n)
    return max(0.1, min(1.0, score))

def generate_suggestions(user: Dict[str,Any], history: List[Dict[str,Any]], max_suggestions: int = 2) -> List[Dict[str,Any]]:
    uname = user.get("username","there")
    snippets = [c.get("body","") for c in user.get("comments",[])]
    topic = ""
    if snippets:
        topic = max(snippets, key=len)[:80]
    templates = [
        f"Hey u/{uname}, saw your recent comment about '{topic}'. Curious—what's your take on the trade-offs?",
        f"u/{uname} your insights stood out. If you had to pick one improvement for that, what would it be?"
    ]
    out = []
    for t in templates[:max_suggestions]:
        out.append({"text": t, "score": round(_score_from_comments(user.get('comments', [])), 2)})
    return out
