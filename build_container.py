#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="Interactive/CLI builder for the Abaqus Apptainer container.")
    
    # Define command line arguments
    parser.add_argument("--def-file", help="Path to the Apptainer recipe (.def) file")
    parser.add_argument("--out-file", help="Output container name (.sif)")
    parser.add_argument("--make-jobs", type=int, help="Number of parallel make jobs for compilation")
    parser.add_argument("--marmot-dir", help="Path to the Marmot directory on the host")
    parser.add_argument("--marmot-interface", help="Path to the Abaqus-MarmotInterface directory on the host")
    parser.add_argument("--usub-type", choices=['standard', 'explicit'], help="Compile Standard (user.cpp) or Explicit (user_explicit.cpp)")
    parser.add_argument("--tmp-dir", help="Directory for Apptainer temporary build files (needs 30GB+ space)")

    args = parser.parse_args()

    print("=== Abaqus Apptainer Build Configurator ===\n")

    # Interactive fallbacks for missing arguments
    if args.def_file is None:
        def_input = input("Enter path to Apptainer recipe (.def) file [default: abaqus.def]: ").strip()
        args.def_file = def_input if def_input else "abaqus.def"

    if args.out_file is None:
        out_input = input("Enter output container name (.sif) [default: abaqus_2026.sif]: ").strip()
        args.out_file = out_input if out_input else "abaqus_2026.sif"

    if args.make_jobs is None:
        jobs_input = input("Enter number of parallel make jobs [default: 1]: ").strip()
        args.make_jobs = int(jobs_input) if jobs_input.isdigit() else 1

    if args.marmot_dir is None:
        marmot_input = input("Enter path to host Marmot directory [leave blank to skip]: ").strip()
        args.marmot_dir = marmot_input if marmot_input else None

    if args.marmot_dir and args.marmot_interface is None:
        interface_input = input("Enter path to host Abaqus-MarmotInterface directory: ").strip()
        args.marmot_interface = interface_input if interface_input else None

    if args.marmot_dir and args.usub_type is None:
        type_input = input("Select subroutine to compile ('standard' or 'explicit') [default: standard]: ").strip().lower()
        args.usub_type = type_input if type_input in ['standard', 'explicit'] else 'standard'

    if args.tmp_dir is None:
        tmp_input = input("Enter path for Apptainer temp build folder (requires 30GB+ space) [default: ./apptainer_tmp]: ").strip()
        args.tmp_dir = tmp_input if tmp_input else "./apptainer_tmp"

    # Verify definition file exists
    if not os.path.isfile(args.def_file):
        print(f"\n[ERROR] Recipe file '{args.def_file}' not found.")
        sys.exit(1)

    # Prepare the environment variables for the %setup block and Apptainer execution
    build_env = os.environ.copy()
    
    # Set up the high-capacity temporary directory
    os.makedirs(args.tmp_dir, exist_ok=True)
    build_env["APPTAINER_TMPDIR"] = os.path.abspath(args.tmp_dir)
    print(f"\n[INFO] Configured Apptainer temporary directory to: {build_env['APPTAINER_TMPDIR']}")

    if args.marmot_dir and args.marmot_interface:
        build_env["MARMOT_DIR"] = os.path.abspath(args.marmot_dir)
        build_env["MARMOT_INTERFACE_DIR"] = os.path.abspath(args.marmot_interface)
    
    sandbox_dir = "tmp_abaqus_sandbox"

    try:
        # =====================================================================
        # STEP 1: Build the Writable Sandbox
        # =====================================================================
        print("\n[STEP 1/3] Building writable sandbox environment (This takes a while)...")
        cmd1 = [
            "sudo", "-E", "apptainer", "build", "--sandbox", 
            "--build-arg", f"MAKE_JOBS={args.make_jobs}", 
            sandbox_dir, args.def_file
        ]
        subprocess.run(cmd1, env=build_env, check=True)

        # =====================================================================
        # STEP 2: Shell in and compile the subroutine
        # =====================================================================
        if args.marmot_dir and args.marmot_interface:
            compile_type = "user_explicit.cpp" if args.usub_type == "explicit" else "user.cpp"
            print(f"\n[STEP 2/3] Shelling into sandbox to compile Marmot {args.usub_type.capitalize()} subroutine ({compile_type})...")
            
            compile_env = build_env.copy()

            # Construct the abaqus make command dynamically based on selection
            make_command = f"cd /projects/Abaqus-MarmotInterface && abaqus make library={compile_type} verbose=3"

            cmd2 = [
                "sudo", "-E", "apptainer", "exec", "--writable", sandbox_dir,
                "bash", "-c", make_command
            ]
            subprocess.run(cmd2, env=compile_env, check=True)
            print("[SUCCESS] Subroutine compiled successfully inside the sandbox.")
        else:
            print("\n[STEP 2/3] Skipping subroutine compilation (No Marmot directories provided).")

        # =====================================================================
        # STEP 3: Freeze to SIF and Cleanup
        # =====================================================================
        print("\n[STEP 3/3] Freezing sandbox into final read-only .sif image...")
        cmd3 = ["sudo", "-E", "apptainer", "build", args.out_file, sandbox_dir]
        subprocess.run(cmd3, env=build_env, check=True)

        print("\n[CLEANUP] Removing temporary sandbox and temp build files...")
        subprocess.run(["sudo", "rm", "-rf", sandbox_dir], check=True)
        # Optionally, you can also clean up the apptainer_tmp directory here if you don't need it cached
        # subprocess.run(["sudo", "rm", "-rf", args.tmp_dir], check=True)

        print(f"\n[DONE] Container fully built and ready: {args.out_file}")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Process failed with exit code {e.returncode}.")
        print("[NOTE] The temporary directories may still exist. You can delete them manually.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[ABORTED] Build cancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
