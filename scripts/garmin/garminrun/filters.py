"""What does not get published.

Both signals ride on the activity list payload, so checking them costs no extra
API call.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class FilterRules(NamedTuple):
    """The publish policy, separated from where it came from.

    publish_decision used to read an argparse.Namespace, which meant a caller
    had to be a CLI to ask the question, and a test had to fake one with
    exactly the right attribute names.
    """

    private_markers: tuple[str, ...]
    allowed_privacy: frozenset[str] = frozenset()
    no_content_filter: bool = False


# What does not get published. Both signals ride on the activity list payload,
# so checking them costs no extra API call.
PRIVATE_MARKERS = ("#nopost", "#private")


def _has_marker(text: str, marker: str) -> bool:
    """True when `marker` appears as a whole token.

    '#' is not a word character, so only the trailing guard matters: #nopost
    must not fire on #nopostcard.
    """
    return re.search(rf"{re.escape(marker)}(?!\w)", text, re.IGNORECASE) is not None


def strip_markers(text: str, markers: tuple[str, ...] = PRIVATE_MARKERS) -> str:
    """Remove the private markers and tidy the whitespace they leave behind.

    Applied to every post, published or not, so a --no-content-filter rescue
    run cannot leak the token into a published page.
    """
    for marker in markers:
        text = re.sub(rf"{re.escape(marker)}(?!\w)", "", text, flags=re.IGNORECASE)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def publish_decision(
    activity: dict, rules: FilterRules, for_retract: bool = False
) -> tuple[bool, str]:
    """Return (publish?, reason). The reason is printed, never written to a
    tracked file.

    Two rules, both free, because activityName and description are already on
    the get_activities_by_date payload:

      - a #nopost marker in the name or the description. Typed on the phone, in
        the same box the post prose is written in.
      - no description at all. Nothing written about it means it was not
        written for the blog.

    Garmin's own privacy.typeKey is available too, but every activity is
    "groups" today, so a rule on it would be a no-op. --allowed-privacy wires
    it up for whenever that changes.

    for_retract drops the description rule. Re-checking an already-published
    post asks a different question: has consent been withdrawn? A marker or a
    privacy change says yes. An empty description says nothing was written,
    which is an absence, not a withdrawal - and prose is often written into the
    post rather than into Garmin, so treating it as a retraction signal would
    cry wolf on those posts twice a day forever.
    """
    if rules.no_content_filter:
        return True, ""

    if rules.allowed_privacy:
        key = ((activity.get("privacy") or {}).get("typeKey") or "").lower()
        if key and key not in rules.allowed_privacy:
            return False, f"privacy={key}"

    name = activity.get("activityName") or ""
    description = activity.get("description") or ""
    for marker in rules.private_markers:
        if _has_marker(f"{name}\n{description}", marker):
            return False, f"marker {marker}"

    if not for_retract and not description.strip():
        return False, "no description"

    return True, ""
