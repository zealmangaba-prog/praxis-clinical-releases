import datetime
import pytest
from streamlit.testing.v1 import AppTest

@pytest.fixture
def app():
    """Initializes and runs app.py up to its initial rendered state."""
    # default_timeout prevents hanging if a loop freezes
    at = AppTest.from_file("app.py", default_timeout=15)
    at.run()
    return at


def test_app_startup_clean(app):
    """Smoke test: Ensures the app starts with zero unhandled exceptions."""
    assert not app.exception, f"App crashed on initial load: {app.exception}"


def test_toggle_all_optional_checkboxes(app):
    """
    Rerun test: Toggles all checkboxes to trigger hidden conditional branches.
    This specifically catches NameErrors from uninitialized form variables.
    """
    for checkbox in app.checkbox:
        # Toggle checkbox on
        checkbox.check().run()
        assert not app.exception, f"Crash after checking '{checkbox.label}': {app.exception}"
        
        # Toggle checkbox off
        checkbox.uncheck().run()
        assert not app.exception, f"Crash after unchecking '{checkbox.label}': {app.exception}"


def test_date_picker_weekend_resilience(app):
    """
    State test: Feeds Saturday and Sunday directly into date input widgets
    to ensure date ranges and session generators do not throw OverflowErrors.
    """
    if app.date_input:
        saturday = datetime.date(2026, 10, 10)
        sunday = datetime.date(2026, 10, 11)

        for weekend_date in [saturday, sunday]:
            # Set the primary date picker to a weekend
            app.date_input[0].set_value(weekend_date).run()
            assert not app.exception, f"Crash when setting date to {weekend_date}: {app.exception}"


def test_full_report_generation_simulation(app):
    """
    Workflow test: Simulates a practitioner filling out key text inputs,
    selecting a scheme, and clicking the generate button.
    """
    # 1. Fill in patient text input if present
    patient_inputs = [ti for ti in app.text_input if "patient" in ti.label.lower()]
    if patient_inputs:
        patient_inputs[0].input("Jane Doe").run()
        assert not app.exception

    # 2. Select diagnosis or preset if selectbox exists
    if app.selectbox:
        # Pick the second option if available
        if len(app.selectbox[0].options) > 1:
            app.selectbox[0].select_index(1).run()
            assert not app.exception

    # 3. Simulate clicking the primary generate/export button
    generate_buttons = [
        btn for btn in app.button 
        if any(word in btn.label.lower() for word in ["generate", "export", "create"])
    ]
    
    if generate_buttons:
        generate_buttons[0].click().run()
        assert not app.exception, f"Crash on report generation click: {generate_buttons[0].label}: {app.exception}"