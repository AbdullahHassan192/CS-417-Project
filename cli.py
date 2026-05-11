from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from extraction import process_pdfs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TALASH pre-processing: PDF CVs to relational CSV using Gemini structured outputs."
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        help="Path to a single CV PDF or a directory containing CV PDFs.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Path to a single CV PDF or a directory containing CV PDFs.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory to store relational CSV files (default: output).",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.1-flash-lite-preview",
        help="Gemini model name (default: gemini-3.1-flash-lite-preview).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API key (optional if GEMINI_API_KEY is set).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output CSV files instead of appending to existing rows.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

    args = parse_args()

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key missing. Set GEMINI_API_KEY or pass --api-key.")

    input_value = args.input or args.input_path
    if not input_value:
        raise ValueError("Input path missing. Provide either positional input_path or --input.")

    input_path = Path(input_value)
    output_dir = Path(args.output_dir)
    append = not args.overwrite

    process_pdfs(
        input_path=input_path,
        output_dir=output_dir,
        api_key=api_key,
        model_name=args.model,
        append=append,
    )
