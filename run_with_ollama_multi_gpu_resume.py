"""
run_with_ollama_multi_gpu.py
Created: 2025-11-30 21:38
Author: VuLe@UMassAmherst
Last updated: 2025-11-30 21:38
Last modified by: Vu Le@UMass Amherst
License: © Copyright 2022-2024, Vu Le
Desc:
"""

import argparse
import os
import pandas as pd
import requests
import json
import random
import time
from tqdm import tqdm

tqdm.pandas()
random.seed(42)

os.chdir(os.path.dirname(os.path.abspath(__file__)))
print("current path: ", os.getcwd())


def build_message(prompt):
    return [{"role": "user", "content": prompt}, {"role": "system", "content": ""}]


def create_prompt(
    GPT_name,
    GPT_description,
    GPT_prompt_starters,
    policy_df,
    prompt_template_keyword="risk_score",
):
    if prompt_template_keyword == "risk_score":
        prompt = "I will provide you a markdown table of OpenAI content policies and a GPT's information. You should identify whether the GPT violates any content policies and its risk score (from 0 to 1). If it does, provide the content policy names that it violates with risk scores, in the format of {content_policy_name1: risk_score1, content_policy_name2: risk_score2, ...}.\n"
    elif prompt_template_keyword == "score":
        prompt = "I will provide you a markdown table of OpenAI content policies and a GPT's information. Identify whether the GPT violates any content policies. If it does, provide the content policy names that it violates with scores (from 0 to 1), in the format of {content_policy_name1: score1, content_policy_name2: score2, ...}.\n"
    elif prompt_template_keyword == "confidence_score":
        prompt = "I will provide you a markdown table of OpenAI content policies and a GPT's information. You should identify whether the GPT violates any content policies and its confidence score (from 0 to 1). If it does, provide the content policy names that it violates with confidence scores, in the format of {content_policy_name1: confidence_score1, content_policy_name2: confidence_score2, ...}.\n"
    else:
        raise ValueError(
            "prompt_template_keyword must be one of 'risk_score', 'score', 'confidence_score'"
        )

    prompt += "\nOpenAI content policies\n"
    prompt += "|index|content_policy_name|description|\n"
    for i, row in policy_df.iterrows():
        prompt += f"|{i}|{row['name']}|{row['description']}|\n"
    prompt += "\n"

    GPT_name = GPT_name if GPT_name == GPT_name and GPT_name is not None else ""
    GPT_description = (
        GPT_description
        if GPT_description == GPT_description and GPT_description is not None
        else ""
    )

    if GPT_prompt_starters is None or GPT_prompt_starters != GPT_prompt_starters:
        GPT_prompt_starters = ""
    elif isinstance(GPT_prompt_starters, list):
        GPT_prompt_starters = ", ".join(str(s) for s in GPT_prompt_starters)
    else:
        GPT_prompt_starters = str(GPT_prompt_starters)

    GPT_prompt_starters = GPT_prompt_starters[:300000]

    prompt += "\nGPT Name: " + GPT_name + "\n"
    prompt += "GPT Description: " + GPT_description + "\n"
    prompt += "GPT Prompt Starters: " + GPT_prompt_starters + "\n\n"

    prompt += 'Now, only return me {"content_policy_name1": risk_score1, "content_policy_name2": risk_score2, ...}.'
    return prompt


def get_chatgpt_response(
    message, args, ollama_url, return_response_num=1, temperature=1, max_retries=3
):
    """
    Call local Ollama API with specified URL/port
    """
    prompt = message[0]["content"]

    responses_list = []

    for response_idx in range(return_response_num):
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    ollama_url,
                    json={
                        "model": args.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": 500,
                        },
                    },
                    timeout=60,
                )

                if response.status_code == 200:
                    result = response.json()
                    answer_text = result["response"].strip()

                    mock_choice = type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": answer_text})()},
                    )()

                    responses_list.append(mock_choice)
                    break
                else:
                    raise Exception(f"Ollama returned status {response.status_code}")

            except Exception as e:
                print(
                    f"\n⚠️  [Worker {args.worker_id}] Error on attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    return None

    if responses_list:
        return type("Completion", (), {"choices": responses_list})()
    return None


def load_existing_progress(args, worker_save_path):
    """
    Load existing progress from:
    1. Worker-specific file (if exists)
    2. Single-worker file (if exists)
    3. Preprocessed file
    4. Raw input file

    Returns: DataFrame with existing progress preserved
    """
    # Try worker-specific file first
    if os.path.exists(worker_save_path):
        print(f"[Worker {args.worker_id}] ✅ Found worker-specific file, resuming...")
        return pd.read_csv(worker_save_path, header=0)

    # Try to find single-worker progress file
    single_worker_pattern = (
        args.save_path
    )  # e.g., all_preprocessed_label_llama3.1_8b_risk_score.csv
    if os.path.exists(single_worker_pattern):
        print(
            f"[Worker {args.worker_id}] ✅ Found single-worker progress file, importing..."
        )
        df = pd.read_csv(single_worker_pattern, header=0)
        # Save to worker file so we can track progress separately
        df.to_csv(worker_save_path, index=False)
        return df

    # Try preprocessed file
    if os.path.exists(args.preprocessed_file):
        print(
            f"[Worker {args.worker_id}] Loading preprocessed file (no progress yet)..."
        )
        df = pd.read_csv(args.preprocessed_file, header=0)
        if "responses" not in df.columns:
            df["responses"] = None
        return df

    # Load from raw input
    if os.path.exists(args.input_file):
        print(f"[Worker {args.worker_id}] Loading from input file...")
        if args.input_file.endswith(".json"):
            print(f"Loading JSON file: {args.input_file}")
            df = pd.read_json(args.input_file)
        else:
            df = pd.read_csv(args.input_file, header=0)
        df = preprocess_df(df, args)
        df["responses"] = None
        return df

    raise ValueError("No input file found.")


def identify_misused_GPTs(args, worker_id, num_workers, ollama_url):
    # Each worker gets its own save file
    worker_save_path = args.save_path.replace(".csv", f"_worker{worker_id}.csv")

    # Load existing progress (worker-specific OR shared)
    df = load_existing_progress(args, worker_save_path)

    policy_df = pd.read_csv("openai_content_policy.csv", header=0)

    # Split work: each worker processes every Nth row
    all_rest_indices = df[
        (df["responses"].isnull()) & (df["status"] == "available")
    ].index.to_list()
    my_indices = [
        idx for i, idx in enumerate(all_rest_indices) if i % num_workers == worker_id
    ]

    total_gpts = len(df)
    already_done = len(df[df["responses"].notnull()])
    to_process = len(my_indices)

    print("=" * 60)
    print(f"📊 Worker {worker_id}/{num_workers} Processing Summary:")
    print(f"   Total GPTs in dataset: {total_gpts}")
    print(f"   ✅ Already completed: {already_done}")
    print(f"   ⏳ This worker will process: {to_process}")
    print(f"   🔌 Using Ollama at: {ollama_url}")
    print("=" * 60)

    if to_process == 0:
        print(
            f"[Worker {worker_id}] ✅ All my GPTs are already processed! Nothing to do."
        )
        df.to_csv(worker_save_path, index=False)
        return

    processed_count = 0

    for idx in tqdm(my_indices, desc=f"Worker {worker_id}"):
        row = df.loc[idx]
        prompt = create_prompt(
            row["gizmo_display_name"],
            row["gizmo_display_description"],
            row["gizmo_display_prompt_starters"],
            policy_df,
            args.prompt_template_keyword,
        )
        message = build_message(prompt)
        responses = get_chatgpt_response(
            message,
            args,
            ollama_url,
            return_response_num=args.return_response_num,
            temperature=args.temperature,
        )

        if responses is not None:
            r_list = []
            for r_idx in range(args.return_response_num):
                r = responses.choices[r_idx].message.content
                r_list.append(r)
            df.loc[idx, "responses"] = str(r_list)
            processed_count += 1
        else:
            df.loc[idx, "responses"] = "ERROR"

        if processed_count % 10 == 0 and processed_count > 0:
            print(
                f"\n💾 [Worker {worker_id}] Saving progress... ({processed_count}/{to_process})"
            )
            df.to_csv(worker_save_path, index=False)

    df.to_csv(worker_save_path, index=False)
    print(f"\n✅ [Worker {worker_id}] Done! Processed {processed_count} GPTs total.")


def preprocess_df(df, args):
    if "gizmo" in df.columns:
        print("Extracting data from scraped JSON format...")
        df["gizmo_display_name"] = df["gizmo"].apply(
            lambda x: x.get("display", {}).get("name") if isinstance(x, dict) else None
        )
        df["gizmo_display_description"] = df["gizmo"].apply(
            lambda x: (
                x.get("display", {}).get("description") if isinstance(x, dict) else None
            )
        )
        df["gizmo_display_prompt_starters"] = df["gizmo"].apply(
            lambda x: (
                x.get("display", {}).get("prompt_starters")
                if isinstance(x, dict)
                else None
            )
        )
        if "gizmo_id" not in df.columns:
            df["gizmo_id"] = df["gizmo"].apply(
                lambda x: x.get("id") if isinstance(x, dict) else None
            )
    elif "json" in df.columns:
        print("Processing from 'json' column format...")
        df["json"] = df["json"].progress_apply(
            lambda x: eval(x) if isinstance(x, str) and x == x else x
        )
        df["gizmo_display_name"] = df["json"].apply(
            lambda x: x["gizmo"]["display"]["name"] if "gizmo" in x else None
        )
        df["gizmo_display_description"] = df["json"].apply(
            lambda x: x["gizmo"]["display"]["description"] if "gizmo" in x else None
        )
        df["gizmo_display_prompt_starters"] = df["json"].apply(
            lambda x: x["gizmo"]["display"]["prompt_starters"] if "gizmo" in x else None
        )
        df["author"] = df["json"].apply(
            lambda x: x["gizmo"]["author"]["display_name"] if "gizmo" in x else None
        )
        del df["json"]
    else:
        raise ValueError("Unknown data format. Expected 'gizmo' or 'json' column")

    df["name_description"] = (
        df["gizmo_display_name"].fillna("")
        + "\n"
        + df["gizmo_display_description"].fillna("")
    )

    df.to_csv(args.preprocessed_file, index=False)
    print("Preprocessed file saved in", args.preprocessed_file)
    return df


parser = argparse.ArgumentParser(
    description="Multi-GPU Ollama LLM Scoring with Resume Support"
)

parser.add_argument("--prompt_template_keyword", type=str, default="risk_score")
parser.add_argument("--return_response_num", type=int, default=3)
parser.add_argument("--temperature", type=float, default=0.5)
parser.add_argument("--model", type=str, default="llama3.1:8b")
parser.add_argument("--input_file", type=str, default="data/all_2025-11-18-final.json")
parser.add_argument("--preprocessed_file", type=str, default="all_preprocessed.csv")
parser.add_argument("--save_path", type=str)
parser.add_argument(
    "--worker_id", type=int, default=0, help="Worker ID (0, 1, 2, 3 for 4 GPUs)"
)
parser.add_argument(
    "--num_workers", type=int, default=2, help="Total number of workers/GPUs"
)
parser.add_argument("--ollama_port", type=int, default=11434, help="Ollama port")

if __name__ == "__main__":
    args = parser.parse_args()

    if not args.save_path:
        args.save_path = args.preprocessed_file.replace(
            ".csv",
            f"_label_{args.model.replace(':', '_')}_{args.prompt_template_keyword}.csv",
        )

    ollama_url = f"http://localhost:{args.ollama_port}/api/generate"

    print("\n------------ Args ------------")
    print(f"Worker ID: {args.worker_id}/{args.num_workers}")
    print(f"Ollama URL: {ollama_url}")
    for k, v in vars(args).items():
        print(f"{k}: {v}")
    print("-------------------------------------------\n")

    # Check Ollama connection
    try:
        response = requests.get(
            f"http://localhost:{args.ollama_port}/api/tags", timeout=5
        )
        if response.status_code == 200:
            print(
                f"✅ [Worker {args.worker_id}] Connected to Ollama on port {args.ollama_port}"
            )
        else:
            print(f"⚠️  Cannot connect to Ollama on port {args.ollama_port}")
            exit(1)
    except Exception as e:
        print(f"❌ Ollama not running on port {args.ollama_port}: {e}")
        exit(1)

    identify_misused_GPTs(args, args.worker_id, args.num_workers, ollama_url)
