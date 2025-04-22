# test_processor.py

from processor import extract_parameters, summarize_config

import os
from dotenv import load_dotenv

load_dotenv()
print("Key:", os.getenv("OPENAI_API_KEY"))  # Debug print


sample_input = "bro video start cheyyandi, prati 4 gantalaki 10 seconds undali, 20 nimishalu feeding mundu , 6-10-2-6"

# Step 1: Extract config from text
params = extract_parameters(sample_input)

# Step 2: Get summary message
summary = summarize_config(params, sample_input)

# Print results
print("----- Final Output -----")
print(summary)
