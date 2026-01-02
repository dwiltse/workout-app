# Data Extraction Summary

## Extraction Process
The raw data comes in an AES-encrypted ZIP file (starting with `309...`). Standard `unzip` tools may fail because of the encryption method.

**Password:** `kOQaqdBx`

### Steps to Extract
1.  **Install `pyzipper`**: The standard Python `zipfile` module does not support AES encryption.
    ```bash
    pip install pyzipper
    ```
2.  **Run Extraction Script**: Use a Python script to handle the decryption.
    ```python
    import pyzipper
    import os

    zip_path = 'raw_data/3091020891_1767064565761.zip' # Update filename as needed
    extract_path = 'raw_data/309_data'
    password = b'kOQaqdBx'

    if not os.path.exists(extract_path):
        os.makedirs(extract_path)

    with pyzipper.AESZipFile(zip_path) as zf:
        zf.pwd = password
        zf.extractall(extract_path)
    ```

## File Contents

### 1. `ACTIVITY` (Recommended for Daily Tracking)
*   **Path:** `ACTIVITY/ACTIVITY_*.csv`
*   **Description:** Daily summary of activity metrics. Best for correlating with daily weight and diet logs.
*   **Columns:**
    *   `date`: Date of record
    *   `steps`: Total daily steps
    *   `distance`: Total distance (meters)
    *   `runDistance`: Distance run (meters)
    *   `calories`: Active calories burned

### 2. `ACTIVITY_STAGE`
*   **Path:** `ACTIVITY_STAGE/ACTIVITY_STAGE_*.csv`
*   **Description:** Activity broken down into specific time segments (e.g., a specific walk or run).
*   **Columns:**
    *   `date`: Date of record
    *   `start`: Start time of segment
    *   `stop`: End time of segment
    *   `distance`: Distance in segment
    *   `calories`: Calories in segment
    *   `steps`: Steps in segment

### 3. `ACTIVITY_MINUTE`
*   **Path:** `ACTIVITY_MINUTE/ACTIVITY_MINUTE_*.csv`
*   **Description:** Minute-by-minute step counts. Useful for visualizing activity patterns throughout the day.
*   **Columns:**
    *   `date`: Date of record
    *   `time`: Time of record
    *   `steps`: Steps taken in that minute
    *   *Note:* Does not contain calorie or distance data.
