"""
core/rules/engine.py
Loads YAML rule definitions for each document type.
The rules are consumed by text_validator.py — this module just provides
structured access to the rule files so adding a new doc type = add one YAML.
"""
import logging
from pathlib import Path
from typing import Dict, List, Any

import yaml

logger = logging.getLogger(__name__)

_RULES_DIR = Path(__file__).parent / "rule_definitions"
_rules_cache: Dict[str, dict] = {}


def load_rules(doc_type: str) -> dict:
    """
    Load and cache rules for a document type.
    Returns empty dict if no rule file exists.
    """
    if doc_type in _rules_cache:
        return _rules_cache[doc_type]

    rule_file = _RULES_DIR / f"{doc_type}.yaml"
    if not rule_file.exists():
        logger.debug("No rule file for doc_type='%s'", doc_type)
        _rules_cache[doc_type] = {}
        return {}

    try:
        with open(rule_file) as fh:
            rules = yaml.safe_load(fh)
        _rules_cache[doc_type] = rules or {}
        logger.debug("Loaded %d rules for '%s'", len(rules.get("rules", [])), doc_type)
    except Exception as exc:
        logger.error("Failed to load rules for '%s': %s", doc_type, exc)
        _rules_cache[doc_type] = {}

    return _rules_cache[doc_type]


def get_rule_patterns(doc_type: str) -> List[Dict[str, Any]]:
    """Return the list of pattern/check rules for a doc type."""
    return load_rules(doc_type).get("rules", [])


def get_required_keywords(doc_type: str) -> List[str]:
    """Return keywords that must be present in a genuine document."""
    return load_rules(doc_type).get("required_keywords", [])


def get_layout_checks(doc_type: str) -> List[Dict[str, Any]]:
    """Return layout check specifications for a doc type."""
    return load_rules(doc_type).get("layout_checks", [])
