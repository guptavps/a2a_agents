# Google Document AI Sample Runbook

## Purpose

This sample uses the Document AI Python SDK to prepare two processors in project `genai-ai-agents-project`:

- `LAYOUT_PARSER_PROCESSOR` for document text, layout, tables, and figures.
- `FORM_PARSER_PROCESSOR` for OCR, general key-value pairs, checkboxes, and conventional tables.

The setup command only discovers, creates, or reuses processors. It does not upload or process a document. Document processing is a later pipeline step and may incur usage charges.

The processors are created in the `us` multi-region. Use a location supported by both processor types; `us` is the configured sample location. The API client endpoint must match the processor location.

## First-Time Google Cloud Setup

1. Select project `genai-ai-agents-project` and confirm billing is enabled.
2. Enable Document AI:

   ```bash
   gcloud services enable documentai.googleapis.com \
     --project=genai-ai-agents-project
   ```

3. Ensure the account used by local Application Default Credentials (ADC) can create processors. The predefined `roles/documentai.editor` role contains `documentai.processors.create`, but also allows processor updates and deletion. Grant it only to the intended creator and only as long as needed. The principal granting this role must itself be allowed to change the project's IAM policy.
4. Configure local ADC and the quota project:

   ```bash
   gcloud auth application-default login
   gcloud auth application-default set-quota-project genai-ai-agents-project
   gcloud auth application-default print-access-token >/dev/null \
     && printf '%s\n' 'ADC ready'
   ```

   Do not paste or commit access tokens or credential files.
5. Create the local virtual environment and install dependencies if this has not already been done:

   ```bash
   cd /Users/vikasg/Documents/python_work/agent_1/a2a/google_doc_ai
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   The `.venv` directory is ignored by Git.

## First Processor Setup

Run a dry run first. It queries the available processor types, creation availability, and supported locations, and checks the named processors. It does not create processors or write the local config:

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/google_doc_ai
.venv/bin/python processor_setup.py --dry-run
```

Review the output. The Layout Parser and Form Parser should both be available and creatable in `us`. Then create or reuse them:

```bash
.venv/bin/python processor_setup.py
```

By default, the script uses:

- Project: `genai-ai-agents-project`
- Location: `us`
- Layout Parser display name: `google-doc-ai-layout-sample`
- Form Parser display name: `google-doc-ai-form-sample`
- Output config: `processor_config.local.json`

The command prints each processor's action (`created` or `reused`), ID, and state. The local config contains project/location and processor resource names/IDs. It is ignored by Git and should remain local.

## Subsequent Runs

The same command is safe to run again:

```bash
.venv/bin/python processor_setup.py
```

For each expected display name, the script lists processors in the configured project/location. If exactly one processor with that name and expected type exists, it reuses it and refreshes `processor_config.local.json`. If none exists, it creates it. If multiple matching names exist or a name is attached to the wrong processor type, the script stops and asks for manual resolution instead of guessing or creating another one.

You can override the project, location, or config path without editing code:

```bash
GOOGLE_CLOUD_PROJECT=another-project \
DOCUMENT_AI_LOCATION=us \
.venv/bin/python processor_setup.py --dry-run

.venv/bin/python processor_setup.py \
  --project another-project \
  --location us \
  --config /path/to/local-processor-config.json
```

The output config path should remain local and must not be committed if it contains resource identifiers for your project.

## How the Setup Script Works

`processor_setup.py` performs these steps:

1. Loads optional local `.env` values, then resolves the project and location from command-line flags, environment variables, or defaults.
2. Connects to the regional Document AI endpoint, for example `us-documentai.googleapis.com`.
3. Lists processor types available to this project/account and prints each target type's creation flag and supported locations.
4. Verifies each type is available, creatable, and supports the selected location.
5. Lists existing processors in that project/location and matches exact configured display names.
6. Reuses a single matching processor of the expected type, or creates one if absent.
7. Writes processor names and IDs to `processor_config.local.json` atomically. Dry-run mode skips creation and config writing.

The script does not delete processors. Processor creation still requires `documentai.processors.create`; seeing `allow_creation=True` from type discovery does not itself grant that IAM permission.

## Troubleshooting

- **API disabled:** enable `documentai.googleapis.com` in the selected project, then retry.
- **Permission denied on create:** confirm the active ADC identity and ask a project IAM administrator to grant the required Document AI role. A successful type-list call does not prove create permission.
- **Processor type unavailable or `allow_creation=False`:** verify the project, account, and location. The script stops before creating a processor.
- **Location mismatch:** create and process with the same supported location. Do not pass a Compute region such as `us-central1` when the processor is in the `us` multi-region.
- **Duplicate display names:** inspect the returned resource names and resolve the duplicates deliberately; the script refuses to pick one.
- **Config missing after a partial run:** rerun the command. It reuses any successfully created processor and continues with the missing one.

## Next Pipeline Step

### Generate the local fixture

Generate the fictional three-page PDF locally:

```bash
cd /Users/vikasg/Documents/python_work/agent_1/a2a/google_doc_ai
.venv/bin/python generate_sample_pdf.py
```

The command writes:

- `output/sample_mixed_document.pdf` — page 1 has selectable PDF text and a vector chart; page 2 is a rasterized scan-style page with text inside the image; page 3 is a labeled loan-application form with key-value pairs and a checkbox.
- `output/sample_scanned_page.png` — the raster source embedded on page 2.

Both files are local generated artifacts under ignored `output/`. This step does not call Google Cloud or incur processing charges. It is safe to rerun; it overwrites these two generated files.

### Process the fixture

First run the local preflight. It checks the processor config, enabled states, PDF path, and online file-size limit. It makes no Document AI API request and incurs no processing charges:

```bash
.venv/bin/python process_sample.py
```

After reviewing the preflight output, explicitly opt in to processing the PDF once with each processor:

```bash
.venv/bin/python process_sample.py --confirm-processing
```

This sends two online processing requests and may incur charges. The command prints the Layout Parser's recognized text and layout-block summary, then the Form Parser's detected key-value fields with confidence values. It also saves the complete processor responses locally:

- `output/document_ai_responses/layout_parser_response.json`
- `output/document_ai_responses/form_parser_response.json`

The `output/` directory is ignored by Git. If the Layout Parser request succeeds but the Form Parser request fails, the first JSON response remains available. Rerunning with `--confirm-processing` submits both requests again and may incur charges again. The sample is three pages and about 100 KB; verify current processor/location limits and pricing before sending real documents.

If a run exits with a Python traceback after printing `Full Document AI response: ...`, inspect that JSON before retrying. A response file means that processor request completed and was billable; an error while formatting the output may happen after that successful API call. Fix/reporting errors can be rerun locally from the saved JSON without another API call, but rerunning `process_sample.py --confirm-processing` sends both processor requests again.
