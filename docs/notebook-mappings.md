# Notebook Mappings Configuration

The pipeline uses a YAML file to map reMarkable notebooks to NotebookLM projects.
Each entry tells the pipeline which reMarkable folder and notebook to read from,
which NotebookLM notebook to upload content to, and where to put AI response PDFs.

## File Location

```
~/.rm_notebooklm/mappings.yaml
```

The path can be overridden via the `RM_NOTEBOOK_MAPPINGS_FILE` environment variable
(or in `.env`).

## Example Configuration

```yaml
mappings:
  - rm_folder: "Work"
    rm_notebook: "Meeting Notes"
    notebooklm_nb_id: "projects/123456789/locations/us-central1/notebooks/abc-def-ghi"
    responses_folder: "responses"
    notebooklm_path: "C"

  - rm_folder: "Personal"
    rm_notebook: "Research Ideas"
    notebooklm_nb_id: "projects/123456789/locations/us-central1/notebooks/xyz-uvw-rst"
    responses_folder: "AI Responses"
    notebooklm_path: null
```

## Field Reference

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `rm_folder` | string | yes | — | Exact name of the reMarkable folder containing the notebook |
| `rm_notebook` | string | yes | — | Exact name of the reMarkable notebook (document) within the folder |
| `notebooklm_nb_id` | string | yes | — | NotebookLM notebook ID (see below for how to find this) |
| `responses_folder` | string | no | `"responses"` | Name of the subfolder within `rm_folder` where AI response PDFs are uploaded |
| `notebooklm_path` | `"A"`, `"B"`, `"C"`, or `null` | no | `null` | Override the global `NOTEBOOKLM_PATH` setting for this notebook only; `null` uses the global setting |

## Finding Your NotebookLM Notebook ID

**Path C (Gemini grounding — recommended):** The notebook ID is the resource name of
your Gemini corpus. You can find it in the Google Cloud Console under
Vertex AI > Generative AI > Corpora, or by calling the Gemini Grounding API
and inspecting the `name` field of the corpus resource.

**Path B (Enterprise API):** The notebook ID is the full resource name in the format
`projects/{project_number}/locations/{location}/notebooks/{notebook_id}`.
Retrieve it from the NotebookLM Enterprise API or Google Cloud Console.

**Path A (unofficial notebooklm-py):** The notebook ID is the UUID visible in the
NotebookLM web app URL when you open a notebook:
`https://notebooklm.google.com/notebook/{notebook-uuid}`.

## Behavior When the File Is Missing

If `~/.rm_notebooklm/mappings.yaml` does not exist, the pipeline logs a
`mappings_file_not_found` info message and returns an empty mapping list.
No error is raised. The pipeline will simply skip all notebook processing
and exit cleanly.

This is intentional: first-run setups without a mappings file produce no
side effects.

## Notes

- Folder and notebook names are matched exactly (case-sensitive).
- The `responses_folder` subfolder is looked up inside `rm_folder`. If it does
  not exist, `rm_responses_folder_id` will be `None` and uploads to that
  folder will fail until the folder is created on the reMarkable device.
- A single notebook can only appear in one mapping entry. Duplicate entries
  for the same `(rm_folder, rm_notebook)` pair will result in the last one
  taking effect when resolved.
