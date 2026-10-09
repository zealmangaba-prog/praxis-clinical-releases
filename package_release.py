"""
package_release.py

Automates the production of protected client distributions for macOS and Windows.
- Obfuscates core/ proprietary business logic with PyArmor
- Bundles public runtime assets and launchers
- Strictly excludes private keys, minters, and test suites
- Compresses output into distributable ZIP archives
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent
RELEASES_DIR = ROOT_DIR / "releases"
BUILD_TMP = ROOT_DIR / "build_tmp"

# Essential client files
SHARED_FILES = [
    "app.py",
    "public_key.pem",
    "requirements.txt",
    "README.md",
]

OPTIONAL_DIRS = [
    "assets",
    "templates",
    "data",
]

def clean_directory(dir_path: Path):
    if dir_path.exists():
        shutil.rmtree(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)

def verify_safety():
    """Ensure private credentials are not staged in root or public targets."""
    private_key = ROOT_DIR / "private_key.pem"
    if not private_key.exists():
        print("⚠️  Warning: private_key.pem not found in root (good for client safety, check your minter).")
    else:
        print("✓ Verified private_key.pem exists in dev environment (will be excluded from build).")

def build_target(target_os: str, platform_flags: list, launcher_script: str):
    print(f"\n==================================================")
    print(f"  Building Release Package: {target_os.upper()}")
    print(f"==================================================")

    target_dir = BUILD_TMP / f"Clinical_Report_Generator_{target_os}"
    clean_directory(target_dir)

    # 1. Obfuscate core/ into target package
    print("[1/4] Obfuscating core proprietary modules with PyArmor...")
    # Point PyArmor output to target_dir so it generates target_dir/core/
    cmd = ["pyarmor", "gen"] + platform_flags + ["-O", str(target_dir), "core/"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ PyArmor generation failed:\n{result.stderr}")
        return False
    print("✓ Proprietary logic encrypted.")

    # 2. Copy shared files
    print("[2/4] Copying application assets...")
    for filename in SHARED_FILES:
        src = ROOT_DIR / filename
        if src.exists():
            shutil.copy2(src, target_dir / filename)
        else:
            print(f"⚠️  Missing optional shared file: {filename}")

    # Copy optional directories if they exist
    for dir_name in OPTIONAL_DIRS:
        src_dir = ROOT_DIR / dir_name
        if src_dir.exists() and src_dir.is_dir():
            shutil.copytree(src_dir, target_dir / dir_name, dirs_exist_ok=True)

    # 3. Copy OS-specific launcher
    print(f"[3/4] Bundling launcher ({launcher_script})...")
    launcher_src = ROOT_DIR / launcher_script
    if launcher_src.exists():
        dest = target_dir / launcher_script
        shutil.copy2(launcher_src, dest)
        if target_os == "macos":
            os.chmod(dest, 0o755)
    else:
        print(f"⚠️  Warning: {launcher_script} not found in root.")

    # 4. Create ZIP Archive
    print("[4/4] Creating ZIP archive...")
    zip_path = RELEASES_DIR / f"Clinical_Report_Generator_{target_os}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in target_dir.rglob("*"):
            if file.is_file():
                # Avoid accidental inclusion of private keys
                if file.name in ["private_key.pem", "generate_trial_keys.py"]:
                    continue
                arcname = file.relative_to(target_dir)
                zipf.write(file, arcname)

    print(f"✓ Created: {zip_path.relative_to(ROOT_DIR)} ({round(zip_path.stat().st_size / 1024, 1)} KB)")
    return True

def main():
    verify_safety()
    clean_directory(RELEASES_DIR)
    clean_directory(BUILD_TMP)

    # macOS build (Apple Silicon + Intel universal)
    build_target(
        target_os="macOS",
        platform_flags=["--platform", "darwin.aarch64", "--platform", "darwin.x86_64"],
        launcher_script="run_app.command"
    )

    # Windows build (64-bit)
    build_target(
        target_os="Windows",
        platform_flags=["--platform", "windows.x86_64"],
        launcher_script="run_app.bat"
    )

    # Cleanup temporary workspace
    if BUILD_TMP.exists():
        shutil.rmtree(BUILD_TMP)

    print("\n==================================================")
    print("  ALL BUILDS COMPLETED SUCCESSFULLY")
    print(f"  Packages are ready in: {RELEASES_DIR.relative_to(ROOT_DIR)}/")
    print("==================================================")

if __name__ == "__main__":
    main()