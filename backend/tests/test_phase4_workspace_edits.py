"""Phase 4 workspace edits remain structured, scoped, and server-checkable."""

from app.services.constraint_engine import (
    RefinementAction,
    apply_scoped_refinement,
    parse_refinement_instruction,
)


def _plan() -> dict:
    return {
        "day_plans": [
            {
                "day_number": 1,
                "activities": [
                    {
                        "name": "City Museum",
                        "start_time": "09:00",
                        "end_time": "10:00",
                        "duration_minutes": 60,
                        "is_locked": False,
                    },
                ],
                "backup_activities": [],
            },
            {
                "day_number": 2,
                "activities": [
                    {
                        "name": "Amber Fort",
                        "start_time": "09:00",
                        "end_time": "10:00",
                        "duration_minutes": 60,
                        "is_locked": False,
                    },
                ],
                "backup_activities": [],
            },
        ],
    }


def test_workspace_move_is_scoped_to_source_and_target_days():
    instruction = parse_refinement_instruction('Move activity "City Museum" from day 1 to day 2.')
    assert instruction.action == RefinementAction.MOVE_ACTIVITY
    updated, changed_days, changed = apply_scoped_refinement(_plan(), instruction)

    assert changed is True
    assert changed_days == {1, 2}
    assert updated["day_plans"][0]["activities"] == []
    assert [activity["name"] for activity in updated["day_plans"][1]["activities"]] == ["Amber Fort", "City Museum"]


def test_workspace_activity_controls_parse_to_deterministic_actions():
    delete = parse_refinement_instruction('Delete activity "Amber Fort" from day 2.')
    duration = parse_refinement_instruction('Set duration for activity "City Museum" on day 1 to 120 minutes.')
    lock = parse_refinement_instruction('Lock activity "City Museum" on day 1.')
    add = parse_refinement_instruction('Add custom activity "Sunset walk" to day 2.')
    regenerate = parse_refinement_instruction("Regenerate day 2.")

    assert delete.action == RefinementAction.DELETE_ACTIVITY
    assert duration.action == RefinementAction.EDIT_DURATION
    assert duration.duration_minutes == 120
    assert lock.action == RefinementAction.LOCK_ACTIVITY
    assert add.action == RefinementAction.ADD_CUSTOM_ACTIVITY
    assert regenerate.action == RefinementAction.REGENERATE_DAY


def test_locked_activity_cannot_be_deleted_by_workspace_command():
    plan = _plan()
    plan["day_plans"][0]["activities"][0]["is_locked"] = True
    instruction = parse_refinement_instruction('Delete activity "City Museum" from day 1.')
    updated, changed_days, changed = apply_scoped_refinement(plan, instruction)

    assert changed is False
    assert changed_days == set()
    assert updated["day_plans"][0]["activities"][0]["name"] == "City Museum"
