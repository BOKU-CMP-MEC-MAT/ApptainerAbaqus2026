#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="Update and recompile Marmot Core inside an existing Apptainer sandbox.")
    
    parser.add_argument("--sandbox", help="Path to the existing Apptainer sandbox directory")
    parser.add_argument("--marmot-dir", help="Path to the updated Marmot directory on the host")
    parser.add_argument("--make-jobs", type=int, help="Number of parallel make jobs for CMake compilation")

    args = parser.parse_args()

    print("=== Marmot Core Sandbox Updater & Compiler ===\n")

    # Interactive fallbacks
    if args.sandbox is None:
        sandbox_input = input("Enter path to existing Apptainer sandbox directory: ").strip()
        args.sandbox = sandbox_input if sandbox_input else None

    if not args.sandbox:
        print("\n[ERROR] Sandbox path is required.")
        sys.exit(1)

    # Validate that the target is actually a sandbox (directory) and not a frozen image
    if not os.path.exists(args.sandbox):
        print(f"\n[ERROR] The path '{args.sandbox}' does not exist.")
        sys.exit(1)
    
    if os.path.isfile(args.sandbox) or args.sandbox.endswith('.sif'):
        print(f"\n[ERROR] '{args.sandbox}' is a file (likely a frozen .sif).")
        print("This script can only update writable sandbox directories. Aborting.")
        sys.exit(1)

    if args.marmot_dir is None:
        marmot_input = input("Enter path to host Marmot directory [leave blank to skip updating files]: ").strip()
        args.marmot_dir = marmot_input if marmot_input else None

    if args.make_jobs is None:
        jobs_input = input("Enter number of parallel make jobs for CMake [default: 1]: ").strip()
        args.make_jobs = int(jobs_input) if jobs_input.isdigit() else 1

    try:
        # =====================================================================
        # STEP 1: Sync Host Folders to Sandbox
        # =====================================================================
        if args.marmot_dir:
            print("\n[STEP 1/2] Syncing updated Marmot directory into the sandbox...")
            
            # Path inside the sandbox
            sb_marmot = os.path.join(args.sandbox, "projects", "Marmot")

            # Remove old directory inside the sandbox using sudo to handle root-owned files
            subprocess.run(["sudo", "rm", "-rf", sb_marmot], check=True)

            # Copy the new directory in
            subprocess.run(["sudo", "cp", "-r", os.path.abspath(args.marmot_dir), sb_marmot], check=True)
            print("[SUCCESS] Host files successfully copied to sandbox.")
        else:
            print("\n[STEP 1/2] No host directory provided. Proceeding to recompile existing sandbox files...")

        # =====================================================================
        # STEP 2: Shell in and Compile
        # =====================================================================
        print("\n[STEP 2/2] Shelling into sandbox to build Marmot Core...")

        # We construct a bash script string to execute inside the container.
        # This handles only the CMake build for Marmot.
        compile_script = f"""
        set -e
        
        # Ensure environment variables are active
        export MARMOT_INSTALL_DIR=/usr/local
        export MARMOT_INSTALL_LIBDIR=lib64
        
        echo "------------------------------------------------"
        echo " Compiling Marmot Core via CMake                "
        echo "------------------------------------------------"
        cd /projects/Marmot
        git clean -x -f || true
        mkdir -p build_ubuntu_gcc
        cd build_ubuntu_gcc
        cmake -DCORE_MODULES='all' -DMATERIAL_MODULES='all' -DELEMENT_MODULES='all' -DCMAKE_INSTALL_PREFIX=/usr/local ..
        make -j{args.make_jobs} install
        """

        cmd = [
            "sudo", "-E", "apptainer", "exec", "--writable", args.sandbox,
            "bash", "-c", compile_script
        ]
        
        subprocess.run(cmd, check=True)
        
        print("\n[DONE] Marmot Core successfully updated and compiled inside the sandbox.")
        print(f"Sandbox Location: {os.path.abspath(args.sandbox)}")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Update process failed with exit code {e.returncode}.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[ABORTED] Update cancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
