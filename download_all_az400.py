"""Download all AZ-400 learning paths."""
import subprocess
import sys

az400_paths = [
    "learn.wwl.az-400-implement-security-validate-code-basescompliance",
    "learn.az-400-develop-instrumentation-strategy",
    "learn.az-400-manage-source-control",
    "learn.az-400-facilitate-communication-collaboration",
    "learn.az-400-develop-sre-strategy",
    "learn.wwl.az-400-implement-continuous-feedback",
    "learn.wwl.az-400-manage-infrastructure-as-code-using-azure",
    "learn.az-400-develop-security-compliance-plan",
    "learn.wwl.az-400-design-implement-release-strategy",
    "learn.az-400-define-implement-continuous-integration",
    "learn.wwl.az-400-implement-secure-continuous-deployment",
    "learn.wwl.az-400-design-implement-dependency-management-strategy",
    "learn.wwl.az-400-implement-ci-azure-pipelines-github-actions",
    "learn.wwl.az-400-work-git-for-enterprise-devops",
]

print(f"Starting download of {len(az400_paths)} AZ-400 learning paths...")
print("=" * 80)

for i, uid in enumerate(az400_paths, 1):
    print(f"\n[{i}/{len(az400_paths)}] Downloading: {uid}")
    print("-" * 80)
    
    # Run the downloader
    result = subprocess.run([
        sys.executable, "main.py",
        "--uid", uid,
        "--format", "pdf",
        "--output", f"./downloads/az-400"
    ], capture_output=False, text=True)
    
    if result.returncode == 0:
        print(f"[OK] Successfully downloaded: {uid}")
    else:
        print(f"[FAIL] Failed to download: {uid}")

print("\n" + "=" * 80)
print("All downloads completed!")
print(f"Location: ./downloads/az-400")
