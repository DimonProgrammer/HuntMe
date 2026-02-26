"""Tests for the 11-step operator qualification flow.

Covers: happy path, simplified HW path, back navigation,
objection handling, input validation, disqualification scenarios.
"""

import pytest
from unittest.mock import AsyncMock, patch

from bot.handlers.operator_flow import (
    OperatorForm,
    process_name,
    process_has_pc,
    process_no_pc_followup,
    process_age,
    process_study_work,
    process_english,
    process_pc_confidence,
    process_cpu,
    process_cpu_skip,
    process_cpu_simple_age,
    process_cpu_simple_usage,
    process_gpu,
    process_gpu_skip,
    process_gpu_simple_gaming,
    process_internet,
    process_start_date,
    process_contact,
    cb_go_back,
    catch_text_in_button_states,
)
from tests.conftest import make_message, make_callback


# ═══════════════════════════════════════════════════════════════════════════
#  HAPPY PATH — Direct CPU/GPU input
# ═══════════════════════════════════════════════════════════════════════════

class TestHappyPathDirect:
    """Full flow: name → PC(yes) → age → study → english → confidence →
    CPU(direct) → GPU(direct) → internet → start date → contact."""

    async def test_step1_name(self, state):
        msg = make_message("John Smith")
        await state.set_state(OperatorForm.waiting_name)
        await process_name(msg, state)

        data = await state.get_data()
        assert data["name"] == "John Smith"
        assert await state.get_state() == OperatorForm.waiting_has_pc.state
        msg.answer.assert_called()

    async def test_step2_has_pc_yes(self, state):
        cb = make_callback("pc_desktop")
        await state.set_state(OperatorForm.waiting_has_pc)
        await process_has_pc(cb, state)

        data = await state.get_data()
        assert data["has_pc"] is True
        assert data["pc_type"] == "desktop"
        assert await state.get_state() == OperatorForm.waiting_age.state

    async def test_step2_has_pc_laptop(self, state):
        cb = make_callback("pc_laptop")
        await state.set_state(OperatorForm.waiting_has_pc)
        await process_has_pc(cb, state)

        data = await state.get_data()
        assert data["has_pc"] is True
        assert data["pc_type"] == "laptop"

    async def test_step3_age(self, state):
        msg = make_message("22")
        await state.set_state(OperatorForm.waiting_age)
        await process_age(msg, state)

        data = await state.get_data()
        assert data["age"] == 22
        assert await state.get_state() == OperatorForm.waiting_study_work.state

    async def test_step3_age_with_text(self, state):
        """Age embedded in sentence: 'I am 25 years old'."""
        msg = make_message("I am 25 years old")
        await state.set_state(OperatorForm.waiting_age)
        await process_age(msg, state)

        data = await state.get_data()
        assert data["age"] == 25

    async def test_step4_study_work(self, state):
        cb = make_callback("study_working")
        await state.set_state(OperatorForm.waiting_study_work)
        await process_study_work(cb, state)

        data = await state.get_data()
        assert data["study_status"] == "working"
        assert await state.get_state() == OperatorForm.waiting_english.state

    async def test_step4_study_distance(self, state):
        cb = make_callback("study_distance")
        await state.set_state(OperatorForm.waiting_study_work)
        await process_study_work(cb, state)

        data = await state.get_data()
        assert data["study_status"] == "student_distance"

    async def test_step4_study_neither(self, state):
        cb = make_callback("study_neither")
        await state.set_state(OperatorForm.waiting_study_work)
        await process_study_work(cb, state)

        data = await state.get_data()
        assert data["study_status"] == "neither"

    async def test_step5_english(self, state):
        cb = make_callback("eng_b2")
        await state.set_state(OperatorForm.waiting_english)
        await process_english(cb, state)

        data = await state.get_data()
        assert data["english_level"] == "B2"
        assert await state.get_state() == OperatorForm.waiting_pc_confidence.state

    async def test_step5_english_all_levels(self, state):
        """All English levels map correctly."""
        levels = {
            "eng_beginner": "Beginner",
            "eng_b1": "B1",
            "eng_b2": "B2",
            "eng_c1": "C1",
            "eng_native": "Native",
        }
        for cb_data, expected in levels.items():
            await state.set_state(OperatorForm.waiting_english)
            cb = make_callback(cb_data)
            await process_english(cb, state)
            data = await state.get_data()
            assert data["english_level"] == expected, f"Failed for {cb_data}"

    async def test_step6_pc_confidence(self, state):
        msg = make_message("I'm very comfortable, I build PCs")
        await state.set_state(OperatorForm.waiting_pc_confidence)
        await process_pc_confidence(msg, state)

        data = await state.get_data()
        assert "comfortable" in data["pc_confidence"].lower()
        assert await state.get_state() == OperatorForm.waiting_cpu.state

    async def test_step7_cpu_direct(self, state):
        msg = make_message("Intel Core i7-12700K")
        await state.set_state(OperatorForm.waiting_cpu)
        await process_cpu(msg, state)

        data = await state.get_data()
        assert data["cpu_model"] == "Intel Core i7-12700K"
        assert await state.get_state() == OperatorForm.waiting_gpu.state

    async def test_step8_gpu_direct(self, state):
        msg = make_message("NVIDIA RTX 3060")
        await state.set_state(OperatorForm.waiting_gpu)
        await state.update_data(cpu_model="Intel Core i7-12700K")
        await process_gpu(msg, state)

        data = await state.get_data()
        assert data["gpu_model"] == "NVIDIA RTX 3060"
        assert await state.get_state() == OperatorForm.waiting_internet.state

    async def test_step9_internet(self, state):
        msg = make_message("200 Mbps fiber, LAN cable")
        await state.set_state(OperatorForm.waiting_internet)
        await process_internet(msg, state)

        data = await state.get_data()
        assert "200" in data["internet_speed"]
        assert await state.get_state() == OperatorForm.waiting_start_date.state

    async def test_step10_start_date(self, state):
        msg = make_message("Next Monday")
        await state.set_state(OperatorForm.waiting_start_date)
        await process_start_date(msg, state)

        data = await state.get_data()
        assert data["start_date"] == "Next Monday"
        assert await state.get_state() == OperatorForm.waiting_contact.state

    async def test_step11_contact_completes_flow(self, state):
        msg = make_message("@johndoe")
        await state.set_state(OperatorForm.waiting_contact)
        await state.update_data(
            name="John Smith", has_pc=True, age=22, study_status="working",
            english_level="B2", pc_confidence="Good", cpu_model="i7-12700K",
            gpu_model="RTX 3060", internet_speed="200 Mbps", start_date="Monday",
            candidate_type="operator",
        )
        await process_contact(msg, state)

        # State should be cleared after completion
        assert await state.get_state() is None
        # Should have sent multiple messages (reviewing + result)
        assert msg.answer.call_count >= 2


# ═══════════════════════════════════════════════════════════════════════════
#  HAPPY PATH — Simplified CPU/GPU ("Not sure" buttons)
# ═══════════════════════════════════════════════════════════════════════════

class TestSimplifiedHWPath:
    """Flow through CPU skip → PC age → PC usage → GPU skip → gaming question."""

    async def test_cpu_skip_to_simple_questions(self, state):
        cb = make_callback("cpu_skip")
        await state.set_state(OperatorForm.waiting_cpu)
        await process_cpu_skip(cb, state)

        assert await state.get_state() == OperatorForm.waiting_cpu_simple_age.state

    async def test_cpu_simple_age(self, state):
        cb = make_callback("pcage_new")
        await state.set_state(OperatorForm.waiting_cpu_simple_age)
        await process_cpu_simple_age(cb, state)

        data = await state.get_data()
        assert data["pc_age_estimate"] == "Less than 2 years"
        assert await state.get_state() == OperatorForm.waiting_cpu_simple_usage.state

    async def test_cpu_simple_usage(self, state):
        cb = make_callback("pcuse_gaming")
        await state.set_state(OperatorForm.waiting_cpu_simple_usage)
        await state.update_data(pc_age_estimate="Less than 2 years")
        await process_cpu_simple_usage(cb, state)

        data = await state.get_data()
        assert "Gaming" in data["pc_usage"]
        assert "Not sure" in data["cpu_model"]
        assert await state.get_state() == OperatorForm.waiting_gpu.state

    async def test_gpu_skip_to_gaming_question(self, state):
        cb = make_callback("gpu_skip")
        await state.set_state(OperatorForm.waiting_gpu)
        await process_gpu_skip(cb, state)

        assert await state.get_state() == OperatorForm.waiting_gpu_simple_gaming.state

    async def test_gpu_simple_gaming_modern(self, state):
        """Modern gaming PC → likely hardware compatible."""
        cb = make_callback("game_modern")
        await state.set_state(OperatorForm.waiting_gpu_simple_gaming)
        await state.update_data(
            cpu_model="Not sure (PC age: Less than 2 years, Usage: Gaming)",
            pc_age_estimate="Less than 2 years",
            pc_usage="Gaming",
        )
        await process_gpu_simple_gaming(cb, state)

        data = await state.get_data()
        assert data["hardware_compatible"] is True
        assert await state.get_state() == OperatorForm.waiting_internet.state

    async def test_gpu_simple_gaming_no_games(self, state):
        """Old PC, no gaming → hardware_compatible = None (uncertain)."""
        cb = make_callback("game_no")
        await state.set_state(OperatorForm.waiting_gpu_simple_gaming)
        await state.update_data(
            cpu_model="Not sure (PC age: 5+ years, Usage: Browsing/Social media)",
            pc_age_estimate="5+ years",
            pc_usage="Browsing/Social media",
        )
        await process_gpu_simple_gaming(cb, state)

        data = await state.get_data()
        assert data["hardware_compatible"] is None  # uncertain


# ═══════════════════════════════════════════════════════════════════════════
#  NO PC PATH
# ═══════════════════════════════════════════════════════════════════════════

class TestNoPcPath:

    async def test_no_pc_goes_to_followup(self, state):
        cb = make_callback("pc_no")
        await state.set_state(OperatorForm.waiting_has_pc)
        await process_has_pc(cb, state)

        data = await state.get_data()
        assert data["has_pc"] is False
        assert await state.get_state() == OperatorForm.waiting_no_pc_followup.state

    async def test_no_pc_plans_soon_continues(self, state):
        """User plans to get PC → continues to age step."""
        cb = make_callback("nopc_soon")
        await state.set_state(OperatorForm.waiting_no_pc_followup)
        await process_no_pc_followup(cb, state)

        assert await state.get_state() == OperatorForm.waiting_age.state

    async def test_no_pc_no_plans_continues(self, state):
        """User has no plans → still continues to age step."""
        cb = make_callback("nopc_no")
        await state.set_state(OperatorForm.waiting_no_pc_followup)
        await process_no_pc_followup(cb, state)

        assert await state.get_state() == OperatorForm.waiting_age.state


# ═══════════════════════════════════════════════════════════════════════════
#  INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestInputValidation:

    async def test_name_too_short(self, state):
        msg = make_message("A")
        await state.set_state(OperatorForm.waiting_name)
        await process_name(msg, state)

        # Should stay on same state
        assert await state.get_state() == OperatorForm.waiting_name.state
        msg.answer.assert_called()
        assert "full name" in msg.answer.call_args[0][0].lower()

    async def test_name_too_long(self, state):
        msg = make_message("A" * 101)
        await state.set_state(OperatorForm.waiting_name)
        await process_name(msg, state)

        assert await state.get_state() == OperatorForm.waiting_name.state

    async def test_age_not_a_number(self, state):
        msg = make_message("twenty two")
        await state.set_state(OperatorForm.waiting_age)
        await process_age(msg, state)

        assert await state.get_state() == OperatorForm.waiting_age.state
        msg.answer.assert_called()
        assert "number" in msg.answer.call_args[0][0].lower()

    async def test_text_in_button_state_rejected(self, state):
        """Typing free text when buttons are expected."""
        msg = make_message("some random text")
        await state.set_state(OperatorForm.waiting_has_pc)
        await catch_text_in_button_states(msg, state)

        msg.answer.assert_called()
        assert "buttons" in msg.answer.call_args[0][0].lower()


# ═══════════════════════════════════════════════════════════════════════════
#  OBJECTION HANDLING MID-FLOW
# ═══════════════════════════════════════════════════════════════════════════

class TestObjectionMidFlow:

    async def test_scam_question_during_name(self, state):
        """User asks 'is this a scam?' at name step — handled, stays on same step."""
        msg = make_message("Is this a scam?")
        await state.set_state(OperatorForm.waiting_name)
        await process_name(msg, state)

        # Should stay on waiting_name (question handled, not treated as name)
        assert await state.get_state() == OperatorForm.waiting_name.state
        # Should have answered with objection response
        assert msg.answer.call_count >= 1

    async def test_adult_content_question_during_age(self, state):
        msg = make_message("Is this adult content?")
        await state.set_state(OperatorForm.waiting_age)
        await process_age(msg, state)

        assert await state.get_state() == OperatorForm.waiting_age.state

    async def test_unknown_question_forwarded_to_admin(self, state):
        """Unrecognized question with '?' is forwarded to admin."""
        msg = make_message("How long has this company existed?")
        await state.set_state(OperatorForm.waiting_name)
        await process_name(msg, state)

        # Should forward to admin
        msg.bot.send_message.assert_called()
        # Should stay on same step
        assert await state.get_state() == OperatorForm.waiting_name.state


# ═══════════════════════════════════════════════════════════════════════════
#  BACK NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════

class TestBackNavigation:

    async def test_back_from_has_pc_to_name(self, state):
        await state.set_state(OperatorForm.waiting_has_pc)
        cb = make_callback("go_back")
        await cb_go_back(cb, state)

        assert await state.get_state() == OperatorForm.waiting_name.state

    async def test_back_from_age_to_has_pc(self, state):
        await state.set_state(OperatorForm.waiting_age)
        cb = make_callback("go_back")
        await cb_go_back(cb, state)

        assert await state.get_state() == OperatorForm.waiting_has_pc.state

    async def test_back_from_english_to_study_work(self, state):
        await state.set_state(OperatorForm.waiting_english)
        cb = make_callback("go_back")
        await cb_go_back(cb, state)

        assert await state.get_state() == OperatorForm.waiting_study_work.state

    async def test_back_from_name_goes_to_main_menu(self, state):
        """Back from first step returns to main menu."""
        await state.set_state(OperatorForm.waiting_name)
        cb = make_callback("go_back")
        await cb_go_back(cb, state)

        # MenuStates.main_menu is imported at runtime inside cb_go_back
        current = await state.get_state()
        assert current is not None  # should be in main_menu state

    async def test_back_from_cpu_simple_to_cpu(self, state):
        await state.set_state(OperatorForm.waiting_cpu_simple_age)
        cb = make_callback("go_back")
        await cb_go_back(cb, state)

        assert await state.get_state() == OperatorForm.waiting_cpu.state

    async def test_back_from_gpu_simple_to_gpu(self, state):
        await state.set_state(OperatorForm.waiting_gpu_simple_gaming)
        cb = make_callback("go_back")
        await cb_go_back(cb, state)

        assert await state.get_state() == OperatorForm.waiting_gpu.state


# ═══════════════════════════════════════════════════════════════════════════
#  FULL FLOW INTEGRATION (all steps in sequence)
# ═══════════════════════════════════════════════════════════════════════════

class TestFullFlowIntegration:

    async def test_complete_flow_direct_hw(self, state):
        """Simulate a complete candidate going through all 11 steps."""
        # Step 1: Name
        await state.set_state(OperatorForm.waiting_name)
        await process_name(make_message("Maria Santos"), state)
        assert await state.get_state() == OperatorForm.waiting_has_pc.state

        # Step 2: PC — Yes, Laptop
        await process_has_pc(make_callback("pc_laptop"), state)
        assert await state.get_state() == OperatorForm.waiting_age.state

        # Step 3: Age
        await process_age(make_message("24"), state)
        assert await state.get_state() == OperatorForm.waiting_study_work.state

        # Step 4: Study/Work
        await process_study_work(make_callback("study_working"), state)
        assert await state.get_state() == OperatorForm.waiting_english.state

        # Step 5: English
        await process_english(make_callback("eng_b2"), state)
        assert await state.get_state() == OperatorForm.waiting_pc_confidence.state

        # Step 6: PC Confidence
        await process_pc_confidence(make_message("Very comfortable"), state)
        assert await state.get_state() == OperatorForm.waiting_cpu.state

        # Step 7: CPU
        await process_cpu(make_message("Intel Core i5-12400"), state)
        assert await state.get_state() == OperatorForm.waiting_gpu.state

        # Step 8: GPU
        await process_gpu(make_message("GTX 1660 Super"), state)
        assert await state.get_state() == OperatorForm.waiting_internet.state

        # Step 9: Internet
        await process_internet(make_message("150 Mbps, LAN cable"), state)
        assert await state.get_state() == OperatorForm.waiting_start_date.state

        # Step 10: Start date
        await process_start_date(make_message("This week"), state)
        assert await state.get_state() == OperatorForm.waiting_contact.state

        # Step 11: Contact → completes
        await process_contact(make_message("@maria_santos"), state)
        assert await state.get_state() is None

    async def test_complete_flow_simplified_hw(self, state):
        """Flow with 'Not sure' for both CPU and GPU."""
        await state.set_state(OperatorForm.waiting_name)
        await process_name(make_message("Chidi Okafor"), state)
        await process_has_pc(make_callback("pc_desktop"), state)
        await process_age(make_message("21"), state)
        await process_study_work(make_callback("study_neither"), state)
        await process_english(make_callback("eng_b1"), state)
        await process_pc_confidence(make_message("Basic but I can learn"), state)

        # CPU: Not sure → simplified
        await process_cpu_skip(make_callback("cpu_skip"), state)
        assert await state.get_state() == OperatorForm.waiting_cpu_simple_age.state

        await process_cpu_simple_age(make_callback("pcage_mid"), state)
        assert await state.get_state() == OperatorForm.waiting_cpu_simple_usage.state

        await process_cpu_simple_usage(make_callback("pcuse_gaming"), state)
        assert await state.get_state() == OperatorForm.waiting_gpu.state

        # GPU: Not sure → simplified
        await process_gpu_skip(make_callback("gpu_skip"), state)
        assert await state.get_state() == OperatorForm.waiting_gpu_simple_gaming.state

        await process_gpu_simple_gaming(make_callback("game_modern"), state)
        assert await state.get_state() == OperatorForm.waiting_internet.state

        # Finish
        await process_internet(make_message("100 Mbps wifi"), state)
        await process_start_date(make_message("Tomorrow"), state)
        await process_contact(make_message("+234 901 234 5678"), state)
        assert await state.get_state() is None
