# Abaqus & Marmot Apptainer Build System

This repository contains automated tools to build, compile, and update a containerized environment for Abaqus (2026) integrated with the Marmot constitutive modeling library. 

Because Abaqus requires proprietary graphical libraries, specific OS spoofing, and license checkouts during user subroutine compilation, these scripts automate the complex "Sandbox Pivot" workflow using Apptainer.

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

If Marmot directories are provided, it performs a **Sandbox Pivot**: it first builds a writable temporary sandbox, shells inside to safely compile the User Subroutine (`.so`) using Abaqus, and then freezes the sandbox into a final, portable, read-only `.sif` image.

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
| `--out-file` | Name of the final frozen image. | `abaqus_2026.sif` |
| `--make-jobs` | Number of CPU cores to use for CMake compilation. | `1` |
| `--marmot-dir` | Path to the host's Marmot source code. | *None* |
| `--marmot-interface`| Path to the host's Abaqus-MarmotInterface code. | *None* |
| `--usub-type` | Compile `standard` (`user.cpp`) or `explicit` (`user_explicit.cpp`). | `standard` |
| `--tmp-dir` | Directory for Apptainer temp files (Prevents "no space left" errors). | `./apptainer_tmp` |

---

## Script 2: `update_marmot.py` (The Rapid Updater)

When developing constitutive models, building a new container from scratch every time takes too long. This script allows you to rapidly sync your updated host code into an **existing, writable sandbox** and recompile only the Marmot Core.

*Note: This script only works on uncompressed sandbox directories, not `.sif` files.*

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
  --sandbox ./my_abaqus_sandbox \
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
   Instead of building a `.sif` file immediately, use standard Apptainer commands to build a permanent sandbox for development:
   ```bash
   sudo APPTAINER_TMPDIR=./tmp apptainer build --sandbox my_dev_sandbox abaqus.def
   ```
2. **Develop & Iterate:**
   Write your new constitutive models in your host Marmot directory. When ready to test, run the updater to sync and compile:
   ```bash
   ./update_marmot.py --sandbox ./my_dev_sandbox --marmot-dir ./src/Marmot --make-jobs 8
   ```
3. **Test in Abaqus:**
   Shell into your sandbox and run your simulations to test the updated subroutines:
   ```bash
   apptainer exec --writable my_dev_sandbox abaqus job=test_job user=user.cpp
   ```
4. **Deploy (Production):**
   Once your code is verified, use `build_abaqus.py` to bake the final code into a read-only `.sif` file for deployment to a cluster.

---

## Troubleshooting

*   **`no space left on device` during build:** 
    Apptainer extracts ~20GB+ of data into `/tmp` by default. Use the `--tmp-dir` argument in `build_abaqus.py` to point to a high-capacity drive.
*   **Cannot find Abaqus License:** 
    If `abaqus make` fails during `build_abaqus.py`, ensure your cluster network allows your current machine to check out a FlexNet token, as compiling subroutines invokes the Abaqus Python parser.
