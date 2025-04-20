#!/bin/bash

# Activate Conda environment
source /home/hue/miniconda3/etc/profile.d/conda.sh
conda activate dark

# Run Playwright script
python -m scripts.create_playwright_from_db

# MultiOn is down as of Feb 14, 2025, so this script is commented out.
# python -m scripts.morph_multion_reasoning_to_scratchpad /home/hue/Desktop/phd/agi/data/db/multion  

# Process database-related transformations
python -m scripts.create_scratchpad_based_on_db ../data/db
python -m scripts.merge_assertions ../data/human/benign_batch ../data/db

# Run main evaluation script
python -m checkers.main "../human/benign_batch" \
                        "../data/human/fell_for_dp" \
                        "../data/human/did_not_fall_for_dp" \
                        "../data/db" \
                        --verbose  

# Data transformation scripts
python -m data_transforms.transform_task_data
python -m data_transforms.transform_task_dp_comparison_data
python -m data_transforms.transform_benign_data
python -m data_transforms.transform_dp_data

# Success message
echo "All evaluations and transformations completed successfully."
