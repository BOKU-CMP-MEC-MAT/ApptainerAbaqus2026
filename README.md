# Abaqus & Marmot Apptainer Build System

This repository contains automated tools to build, compile, and update a containerized environment for Abaqus (2026) integrated with the Marmot constitutive modeling library. 

Because Abaqus requires proprietary graphical libraries and specific OS spoofing, these scripts automate the complex "Sandbox Pivot" workflow using Apptainer, allowing for both rapid sandbox development and final read-only deployments.

## Prerequisites

Before using these scripts, ensure your host system has:
1. **Apptainer** installed and configured.
2. **Root (`sudo`) privileges** (required for building containers and modifying sandboxes).
3. **Storage Space**: At least 30GB of free space for temporary build files.
4. **Source Files**: 
   - The Apptainer recipe (`abaqus.def`).
   - Abaqus installation tarballs (e.g., `2026.AM_SIM_Abaqus_Extend...tar`).
   - Abaqus silent installer XML files (`UserIntentions_CODE.xml`, etc.).
   - (Optional) Marmot and Abaqus-MarmotInterface source directories.

---

## Script 1: `build_abaqus.py` (The Builder)

This script automates the creation of a clean Apptainer image from your recipe file. 

If Marmot directories are provided, it performs a **Sandbox Pivot**: it first builds a writable temporary sandbox and shells inside to safely compile the User Subroutine (`.so`) using Abaqus. Depending on your choice, it will then either freeze the sandbox into a final, portable, read-only `.sif` image, or leave it as a writable `.sbx` directory for active development.

### Usage
Make the script executable:
```bash
chmod +x build_abaqus.py
```

**Option 1: Interactive Mode**
Run the script without arguments to be guided through the setup:
```bash
./build_abaqus.py
```

**Option 2: Command-Line Mode (Automated)**
Pass arguments directly to bypass prompts.
```bash
./build_abaqus.py \
  --def-file abaqus.def \
  --convert yes \
  --out-file abaqus_2026.sif \
  --marmot-dir ./src/Marmot \
  --marmot-interface ./src/Abaqus-MarmotInterface \
  --usub-type standard \
  --make-jobs 8 \
  --tmp-dir /path/to/high/capacity/drive/apptainer_tmp
```

### Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--def-file` | Path to your Apptainer recipe file. | `abaqus.def` |
| `--convert` | Convert the sandbox to a read-only `.sif` image (`yes` or `no`). | `yes` |
| `--out-file` | Name of the final container (defaults to `.sif` or `.sbx`). | Derived from recipe |
| `--make-jobs` | Number of CPU cores to use for CMake compilation. | `1` |
| `--marmot-dir` | Path to the host's Marmot source code. | *None* |
| `--marmot-interface`| Path to the host's Abaqus-MarmotInterface code. | *None* |
| `--usub-type` | Compile `standard` (`user.cpp`) or `explicit` (`user_explicit.cpp`). | `standard` |
| `--tmp-dir` | Directory for Apptainer temp files (Prevents "no space left" errors). | `./apptainer_tmp` |

---

## Script 2: `update_marmot.py` (The Rapid Updater)

When developing constitutive models, building a new container from scratch every time takes too long. This script allows you to rapidly sync your updated host code into an **existing, writable sandbox** (`.sbx`) and recompile only the Marmot Core. It includes protections against host environment (Conda/Mamba) leakage.

*Note: This script only works on uncompressed sandbox directories (`.sbx`), not `.sif` files.*

### Usage
Make the script executable:
```bash
chmod +x update_marmot.py
```

**Option 1: Interactive Mode**
```bash
./update_marmot.py
```

**Option 2: Command-Line Mode**
```bash
./update_marmot.py \
  --sandbox ./my_dev_env.sbx \
  --marmot-dir ./src/Marmot \
  --make-jobs 8
```

### Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--sandbox` | Path to the existing, writable Apptainer sandbox directory. | *Required* |
| `--marmot-dir`| Path to your updated Marmot source directory on the host. | *None* |
| `--make-jobs` | Number of CPU cores to use for CMake compilation. | `1` |

---

## Recommended Workflow for Developers

1. **Initial Setup (Sandbox Mode):**
   Instead of building a read-only image immediately, use the build script to generate a permanent, writable sandbox containing your compiled interface:
   ```bash
   ./build_abaqus.py --convert no --out-file my_dev_env.sbx --marmot-dir ./src/Marmot --marmot-interface ./src/Abaqus-MarmotInterface --make-jobs 8
   ```
2. **Develop & Iterate:**
   Write your new constitutive models in your host Marmot directory. When ready to test, run the updater to sync and compile:
   ```bash
   ./update_marmot.py --sandbox ./my_dev_env.sbx --marmot-dir ./src/Marmot --make-jobs 8
   ```
3. **Test in Abaqus:**
   Shell into your sandbox and run your simulations to test the updated subroutines:
   ```bash
   apptainer exec --writable my_dev_env.sbx abaqus job=test_job user=user.cpp
   ```
4. **Deploy (Production):**
   Once your code is verified and stable, freeze your sandbox into a read-only `.sif` file for deployment to a cluster:
   ```bash
   sudo apptainer build abaqus_production.sif my_dev_env.sbx
   ```

---

## Troubleshooting

*   **`no space left on device` during build:** 
    Apptainer extracts ~20GB+ of data into `/tmp` by default. Use the `--tmp-dir` argument in `build_abaqus.py` to point to a high-capacity drive.
*   **Host Environment Leakage (`Could not find compiler set in environment variable CXX`):**
    If you manually shell into the container, ensure Conda/Mamba is deactivated on your host, or always use the `--cleanenv` flag with `apptainer exec` to prevent your host paths from overriding the container's native GCC 15 compilers.
