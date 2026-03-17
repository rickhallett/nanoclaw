"""XML plan validation for nightctl agent-jobs.

Stateless validation — receives XML strings, returns nothing or raises.
Uses stdlib xml.etree.ElementTree. No external dependencies.

Validation is called at two gates (swiss cheese model):
  1. planning → plan-review: structural check before human reviews
  2. plan-review → in-progress: re-check before execution (catches file edits)
"""

import xml.etree.ElementTree as ET
from pathlib import Path


class PlanValidationError(Exception):
    """Raised when an XML plan fails structural validation.

    Contains all failures, not just the first one.
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_plan_xml(xml_string: str) -> None:
    """Validate an XML plan string against the schema rules.

    Raises PlanValidationError with all failures collected.

    Rules enforced:
      1. Must parse as valid XML with <plan> root
      2. <goal> required, non-empty (stripped)
      3. <steps> required, at least one <step> with 'n' and 'output' attributes
      4. <constraints> required, at least one <constraint>
      5. <success> required, at least one <criterion>

    Not validated: prose quality, dependency validity, output path existence.
    """
    errors: list[str] = []

    # Parse
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        raise PlanValidationError([f"invalid XML: {e}"]) from e

    if root.tag != "plan":
        errors.append(f"root element must be <plan>, got <{root.tag}>")
        raise PlanValidationError(errors)

    # <goal>
    goal = root.find("goal")
    if goal is None:
        errors.append("<goal> is required")
    elif not (goal.text or "").strip():
        errors.append("<goal> must not be empty")

    # <steps>
    steps = root.find("steps")
    if steps is None:
        errors.append("<steps> is required")
    else:
        step_elements = steps.findall("step")
        if not step_elements:
            errors.append("<steps> must contain at least one <step>")
        else:
            for i, step in enumerate(step_elements):
                if step.get("n") is None:
                    errors.append(f"<step> at position {i + 1} missing 'n' attribute")
                if step.get("output") is None:
                    errors.append(f"<step> at position {i + 1} missing 'output' attribute")

    # <constraints>
    constraints = root.find("constraints")
    if constraints is None:
        errors.append("<constraints> is required")
    else:
        constraint_elements = constraints.findall("constraint")
        if not constraint_elements:
            errors.append("<constraints> must contain at least one <constraint>")

    # <success>
    success = root.find("success")
    if success is None:
        errors.append("<success> is required")
    else:
        criterion_elements = success.findall("criterion")
        if not criterion_elements:
            errors.append("<success> must contain at least one <criterion>")

    if errors:
        raise PlanValidationError(errors)


def extract_plan_from_file(content: str) -> str:
    """Extract the first <plan>...</plan> block from file content.

    The file may contain markdown or other prose around the plan.
    Returns the extracted XML string.
    Raises PlanValidationError if no <plan> block found.
    """
    import re

    match = re.search(r"(<plan\b.*?</plan>)", content, re.DOTALL)
    if not match:
        raise PlanValidationError(["no <plan>...</plan> block found in file"])
    return match.group(1)


def validate_plan_ref(plan_ref: str, base_dir: Path) -> str:
    """Resolve a plan_ref path, read the file, extract and validate.

    Returns the extracted XML string on success.
    Raises FileNotFoundError if plan_ref doesn't exist.
    Raises PlanValidationError if extraction or validation fails.
    """
    path = Path(plan_ref)
    if not path.is_absolute():
        path = base_dir / path

    if not path.exists():
        raise FileNotFoundError(f"plan_ref not found: {path}")

    content = path.read_text()
    xml_string = extract_plan_from_file(content)
    validate_plan_xml(xml_string)
    return xml_string
