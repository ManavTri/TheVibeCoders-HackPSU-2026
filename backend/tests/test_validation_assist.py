from app.services.validation.rules.base import NullAssist, ValidationConfig


def test_null_rule_assist_is_no_op_by_default() -> None:
    assist = NullAssist()

    assert assist.suggest_award_matches([], []) == []
    assert assist.classify_line_item("tuition") is None


def test_rule_assist_requires_both_feature_and_llm_flags() -> None:
    default_config = ValidationConfig()
    llm_only = ValidationConfig(llm_enabled=True)
    feature_only = ValidationConfig(rule_assist_enabled=True)

    assert not default_config.llm_enabled and not default_config.rule_assist_enabled
    assert llm_only.llm_enabled and not llm_only.rule_assist_enabled
    assert not feature_only.llm_enabled and feature_only.rule_assist_enabled
