"""Tests for nightctl XML plan validation."""

import pytest
from pathlib import Path

from halos.nightctl.plan import (
    validate_plan_xml,
    extract_plan_from_file,
    validate_plan_ref,
    PlanValidationError,
)


VALID_PLAN = """\
<plan>
  <goal>Research competitor tools</goal>
  <steps>
    <step n="1" output="docs/d2/research.md">Search and analyse</step>
    <step n="2" depends="1" output="stdout">Summarise findings</step>
  </steps>
  <constraints>
    <constraint>Stay within docs/d2/ for new files</constraint>
  </constraints>
  <success>
    <criterion>At least 3 tools compared</criterion>
  </success>
  <output>docs/d2/research.md</output>
</plan>"""


class TestValidatePlanXml:
    def test_valid_plan_passes(self):
        validate_plan_xml(VALID_PLAN)

    def test_malformed_xml_raises(self):
        with pytest.raises(PlanValidationError, match="invalid XML"):
            validate_plan_xml("not xml at all")

    def test_wrong_root_element(self):
        with pytest.raises(PlanValidationError, match="root element must be <plan>"):
            validate_plan_xml("<job><goal>hi</goal></job>")

    def test_missing_goal(self):
        xml = "<plan><steps><step n='1' output='x'>do</step></steps><constraints><constraint>no</constraint></constraints><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<goal> is required" in exc_info.value.errors

    def test_empty_goal(self):
        xml = "<plan><goal>  </goal><steps><step n='1' output='x'>do</step></steps><constraints><constraint>no</constraint></constraints><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<goal> must not be empty" in exc_info.value.errors

    def test_missing_steps(self):
        xml = "<plan><goal>hi</goal><constraints><constraint>no</constraint></constraints><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<steps> is required" in exc_info.value.errors

    def test_empty_steps(self):
        xml = "<plan><goal>hi</goal><steps></steps><constraints><constraint>no</constraint></constraints><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<steps> must contain at least one <step>" in exc_info.value.errors

    def test_step_missing_n_attribute(self):
        xml = "<plan><goal>hi</goal><steps><step output='x'>do</step></steps><constraints><constraint>no</constraint></constraints><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert any("missing 'n' attribute" in e for e in exc_info.value.errors)

    def test_step_missing_output_attribute(self):
        xml = "<plan><goal>hi</goal><steps><step n='1'>do</step></steps><constraints><constraint>no</constraint></constraints><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert any("missing 'output' attribute" in e for e in exc_info.value.errors)

    def test_missing_constraints(self):
        xml = "<plan><goal>hi</goal><steps><step n='1' output='x'>do</step></steps><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<constraints> is required" in exc_info.value.errors

    def test_empty_constraints(self):
        xml = "<plan><goal>hi</goal><steps><step n='1' output='x'>do</step></steps><constraints></constraints><success><criterion>yes</criterion></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<constraints> must contain at least one <constraint>" in exc_info.value.errors

    def test_missing_success(self):
        xml = "<plan><goal>hi</goal><steps><step n='1' output='x'>do</step></steps><constraints><constraint>no</constraint></constraints></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<success> is required" in exc_info.value.errors

    def test_empty_success(self):
        xml = "<plan><goal>hi</goal><steps><step n='1' output='x'>do</step></steps><constraints><constraint>no</constraint></constraints><success></success></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        assert "<success> must contain at least one <criterion>" in exc_info.value.errors

    def test_collects_all_errors(self):
        """Multiple issues reported in one pass, not fail-fast."""
        xml = "<plan><goal></goal></plan>"
        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_xml(xml)
        errors = exc_info.value.errors
        assert len(errors) >= 4  # empty goal + missing steps + missing constraints + missing success


class TestExtractPlanFromFile:
    def test_extracts_from_markdown(self):
        content = "# My Spec\n\nSome prose.\n\n<plan>\n  <goal>Test</goal>\n</plan>\n\nMore prose."
        result = extract_plan_from_file(content)
        assert result.startswith("<plan>")
        assert result.endswith("</plan>")

    def test_no_plan_block_raises(self):
        with pytest.raises(PlanValidationError, match="no <plan>"):
            extract_plan_from_file("just markdown, no plan here")


class TestValidatePlanRef:
    def test_valid_ref(self, tmp_path):
        plan_file = tmp_path / "spec.md"
        plan_file.write_text(f"# Spec\n\n{VALID_PLAN}\n")
        result = validate_plan_ref("spec.md", tmp_path)
        assert "<goal>" in result

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_plan_ref("nonexistent.md", tmp_path)

    def test_invalid_plan_in_file_raises(self, tmp_path):
        plan_file = tmp_path / "bad.md"
        plan_file.write_text("<plan><goal></goal></plan>")
        with pytest.raises(PlanValidationError):
            validate_plan_ref("bad.md", tmp_path)
