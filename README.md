# CS-417-Project
CS-417: Large Language Models

## Preprocessing Runner

### Code Layout

- [models.py](models.py): Pydantic schemas, extraction result dataclass, and table column contracts.
- [normalization.py](normalization.py): Parsing, normalization, and relational row flattening logic.
- [io_csv.py](io_csv.py): CSV append/overwrite persistence helpers.
- [extraction.py](extraction.py): PDF reading, Gemini extraction call, and batch processing orchestration.
- [cli.py](cli.py): Argument parsing and app entry logic.
- [preprocessing_script.py](preprocessing_script.py): Compatibility wrapper so existing commands still work.

### Quick run (single PDF)

```powershell
.\run_preprocessing.ps1 ".\Handler (8)-21-29.pdf"
```

### Quick run (folder ingestion)

```powershell
.\run_preprocessing.ps1 ".\CVs"
```

### Wrapper overwrite mode

```powershell
.\run_preprocessing.ps1 ".\CVs" -Overwrite
```

### Python CLI options

```powershell
# Single PDF (short positional input)
.\.venv\Scripts\python.exe .\preprocessing_script.py ".\Handler (8)-21-29.pdf"

# Folder ingestion (processes all PDFs one by one)
.\.venv\Scripts\python.exe .\preprocessing_script.py ".\CVs"

# Overwrite mode (default behavior is append)
.\.venv\Scripts\python.exe .\preprocessing_script.py ".\CVs" --overwrite
```

Notes:
- By default, output CSV files are appended to, not overwritten.
- Use `--overwrite` on the Python CLI or `-Overwrite` on the PowerShell wrapper when you want fresh CSVs for a new run.
