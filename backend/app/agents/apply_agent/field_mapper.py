from __future__ import annotations

import re
from typing import Optional

from app.agents.apply_agent.application_context import FormField

# Pattern groups map label/name/placeholder text to canonical field types.
# The first matching group wins; order matters from most specific to least specific.

CANONICAL_PATTERNS: list[tuple[str, list[str]]] = [
    ("first_name", [
        r"\bfirst\s*name\b", r"\bfirstname\b", r"\bfname\b", r"\bgiven\s*name\b",
        r"\bforename\b",
    ]),
    ("last_name", [
        r"\blast\s*name\b", r"\blastname\b", r"\blname\b", r"\bsurname\b",
        r"\bfamily\s*name\b", r"\bforename\b",
    ]),
    ("full_name", [
        r"\bfull\s*name\b", r"\byour\s*name\b", r"\bname\b",
    ]),
    ("email", [
        r"\bemail\b", r"\be-?mail\b", r"\belectronic\s*mail\b",
    ]),
    ("phone", [
        r"\bphone\b", r"\btelephone\b", r"\btel\b", r"\bcell\b", r"\bmobile\b",
        r"\bphone\s*number\b",
    ]),
    ("address", [
        r"\baddress\b", r"\bstreet\b", r"\baddress\s*line\b",
    ]),
    ("address_line2", [
        r"\baddress\s*line\s*2\b", r"\bapt\b", r"\bunit\b", r"\bsuite\b",
    ]),
    ("city", [
        r"\bcity\b", r"\btown\b", r"\blocality\b",
    ]),
    ("state", [
        r"\bstate\b", r"\bprovince\b", r"\bregion\b",
    ]),
    ("postal_code", [
        r"\bpostal\s*code\b", r"\bzip\s*code\b", r"\bzip\b", r"\bpostcode\b",
    ]),
    ("country", [
        r"\bcountry\b", r"\bnation\b",
    ]),
    ("company", [
        r"\bcurrent\s*company\b", r"\bemployer\b", r"\bcompany\b",
        r"\borganization\b", r"\borganisation\b",
    ]),
    ("job_title", [
        r"\bjobs?\s*title\b", r"\btitle\b", r"\bposition\b",
        r"\bcurrent\s*position\b",
    ]),
    ("linkedin", [
        r"\blinkedin\b", r"\blinked\s*in\b",
    ]),
    ("portfolio", [
        r"\bportfolio\b", r"\bpersonal\s*website\b", r"\bwebsite\b",
        r"\bgithub\b",
    ]),
    ("start_date", [
        r"\bstart\s*date\b", r"\bdate\s*from\b",
    ]),
    ("end_date", [
        r"\bend\s*date\b", r"\bdate\s*to\b",
    ]),
    ("currently_working", [
        r"\bcurrently\s*(?:working|employed|attending)", r"\bpresent\b",
        r"\bcurrent\s*(?:position|role|job)",
    ]),
    ("education_level", [
        r"\bdegree\b", r"\beducation\b", r"\bqualification\b",
        r"\bhighest\s*degree\b",
    ]),
    ("school", [
        r"\bschool\b", r"\buniversity\b", r"\bcollege\b", r"\binstitution\b",
    ]),
    ("major", [
        r"\bmajor\b", r"\bfield\s*of\s*study\b", r"\bsubject\b",
        r"\bconcentration\b",
    ]),
    ("graduation_year", [
        r"\bgraduation\s*(?:year|date)\b", r"\bgrad\s*year\b",
        r"\byear\s*of\s*graduation\b",
    ]),
    ("skills", [
        r"\bskills?\b", r"\btechnologies?\b", r"\btech\s*stack\b",
    ]),
    ("summary", [
        r"\bsummary\b", r"\bcover\s*letter\b", r"\bintroduction\b",
        r"\bpersonal\s*statement\b", r"\babout\s*(?:me|yourself)\b",
    ]),
    ("gender", [
        r"\bgender\b", r"\bsex\b",
    ]),
    ("race_ethnicity", [
        r"\brace\b", r"\bethnicity\b", r"\bethnic\s*origin\b",
    ]),
    ("veteran", [
        r"\bveteran\b", r"\bmilitary\s*service\b",
    ]),
    ("disability", [
        r"\bdisability\b", r"\bdisabled\b",
    ]),
    ("pronouns", [
        r"\bpronouns?\b",
    ]),
    ("eeo_self_identify", [
        r"\bself-?identify\b", r"\bvoluntary\s*(?:self-?identification|data)\b",
        r"\bequal\s*opportunity\b", r"\beeo\b", r"\bdiversity\b",
    ]),
    ("referred_by", [
        r"\breferred\s*by\b", r"\breferral\b", r"\bhow\s*did\s*you\s*hear\b",
        r"\bsource\b",
    ]),
    ("salary_expectation", [
        r"\bsalary\s*expectation\b", r"\bdesired\s*salary\b",
        r"\bsalary\s*requirement\b", r"\bexpected\s*salary\b",
        r"\bcompensation\b",
    ]),
    ("currency", [
        r"\bcurrency\b",
    ]),
    ("notice_period", [
        r"\bnotice\s*period\b", r"\bnotice\b",
    ]),
    ("relocation", [
        r"\brelocation\b", r"\bwilling\s*to\s*relocate\b",
        r"\bwork\s*authorization\b",
    ]),
    ("visa_sponsorship", [
        r"\bvisa\b", r"\bsponsorship\b",
        r"\bright\s*to\s*work\b",
    ]),
    ("work_authorization", [
        r"\bwork\s*authorization\b", r"\bauthorized\s*to\s*work\b",
        r"\bauthorized\b",
    ]),
    ("language", [
        r"\blanguage\b",
    ]),
    ("certification", [
        r"\bcertification\b", r"\bcertificate\b", r"\blicense\b",
    ]),
    ("work_hours", [
        r"\bwork\s*hours?\b", r"\bavailability\b", r"\bhours?\s*per\s*week\b",
        r"\bfull-?time\b", r"\bpart-?time\b",
    ]),
    ("shift", [
        r"\bshift\b", r"\bday\b", r"\bnight\b", r"\bevening\b",
    ]),
    ("start_date_availability", [
        r"\bstart\s*date\b", r"\bavailable\s*(?:from|to\s*start)\b",
        r"\bwhen\s*can\s*you\s*start\b",
    ]),
    ("reference", [
        r"\breference\b",
    ]),
    ("consent", [
        r"\bconsent\b", r"\bagree\b", r"\bterms\b", r"\bconditions?\b",
        r"\bprivacy\s*policy\b", r"\bachnowledge\b",
    ]),
    ("signature", [
        r"\bsignature\b", r"\besignature\b", r"\belectronic\s*signature\b",
    ]),
    ("date_field", [
        r"\bdate\b",
    ]),
    ("unknown", []),
]


class FieldMapper:
    """Maps detected form fields to canonical field types using pattern matching.

    The mapper uses a set of regex patterns grouped by canonical type.
    It checks label text, name attributes, placeholder text, and
    autocomplete attributes (in that order) to find the best match.

    Usage::

        mapper = FieldMapper()
        canonical = mapper.map_fields(fields)
        first_name_field = canonical.get("first_name")
    """

    def __init__(self) -> None:
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        for canon, patterns in CANONICAL_PATTERNS:
            self._compiled_patterns[canon] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def map_fields(self, fields: list[FormField]) -> dict[str, FormField]:
        """Map a list of detected form fields to canonical types.

        Each field is matched against pattern groups. The first
        matching canonical type wins. If no pattern matches, the
        field is mapped to 'unknown'.

        Args:
            fields: Detected form fields from FormDetector.

        Returns:
            A dictionary mapping canonical field type to the FormField.
            If multiple fields map to the same canonical type, the last one wins.
        """
        result: dict[str, FormField] = {}
        unmapped: list[FormField] = []

        for field in fields:
            canon = self._match_canonical(field)
            if canon and canon != "unknown":
                result[canon] = field
            else:
                unmapped.append(field)

        for field in unmapped:
            result[f"field_{field.name or '_'}{len([k for k in result if k.startswith('field_')])}"] = field

        return result

    def _match_canonical(self, field: FormField) -> Optional[str]:
        """Try to match a single field to a canonical type."""
        # Try autocomplete first (most reliable)
        if field.autocomplete:
            matched = self._match_text(field.autocomplete, use_autocomplete=True)
            if matched:
                return matched

        # Try label text
        if field.label:
            matched = self._match_text(field.label)
            if matched:
                return matched

        # Try placeholder
        if field.placeholder:
            matched = self._match_text(field.placeholder)
            if matched:
                return matched

        # Try name attribute
        if field.name:
            name_clean = field.name.replace("_", " ").replace("-", " ").strip()
            matched = self._match_text(name_clean)
            if matched:
                return matched

        return None

    def _match_text(self, text: str, use_autocomplete: bool = False) -> Optional[str]:
        """Match text against canonical pattern groups."""
        if use_autocomplete:
            from app.agents.apply_agent.form_detector import FormDetector
            return FormDetector.AUTOCOMPLETE_TO_FIELD.get(text.lower())

        for canon, patterns in self._compiled_patterns.items():
            if canon == "unknown":
                continue
            for pattern in patterns:
                if pattern.search(text):
                    return canon
        return None

    def get_unmapped_fields(self, fields: list[FormField], canonical: dict[str, FormField]) -> list[FormField]:
        """Return fields that were not mapped to a known canonical type."""
        mapped_selectors = {f.selector for f in canonical.values()}
        return [f for f in fields if f.selector not in mapped_selectors]
