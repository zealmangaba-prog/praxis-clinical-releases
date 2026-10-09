"""
tests/test_scheme_presets.py
Automated test suite verifying South African medical scheme compliance rules,
doctor practice number requirements, and fallback configurations.
"""

from core.medical_aid_presets import SCHEME_PRESETS, get_scheme_preset


def test_scheme_presets_exist():
    expected_schemes = [
        "Discovery Health",
        "GEMS",
        "Medscheme",
        "Momentum Health",
        "Bestmed",
    ]
    for scheme in expected_schemes:
        preset = get_scheme_preset(scheme)
        assert preset is not None
        assert "admin_name" in preset
        assert "email_portal" in preset
        assert "default_batch_limit" in preset
        assert "guidance_note" in preset


def test_discovery_requires_referring_doctor_pr():
    discovery = get_scheme_preset("Discovery Health")
    assert discovery["requires_referring_pr"] is True
    assert "mentalhealth@discovery.co.za" in discovery["email_portal"]
    assert "care_programme" in discovery
    assert "MHCP" in discovery["care_programme"]


def test_gems_preset_configuration():
    gems = get_scheme_preset("GEMS")
    assert gems["requires_referring_pr"] is True
    assert gems["default_batch_limit"] == 6
    assert "Prime Cure" in gems["email_portal"] or "gems.gov.za" in gems["email_portal"]


def test_medscheme_configuration():
    medscheme = get_scheme_preset("Medscheme")
    assert medscheme["default_batch_limit"] == 8
    assert "psychauth@medscheme.co.za" in medscheme["email_portal"]


def test_fallback_preset_for_unknown_scheme():
    unknown = get_scheme_preset("NonExistentScheme 123")
    assert unknown["admin_name"] == "Independent Medical Scheme / Private Healthcare"
    assert unknown["requires_referring_pr"] is False
    assert unknown["default_batch_limit"] == 6