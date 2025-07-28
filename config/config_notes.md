### Logging Configuration: log_level

The `"log_level"` key controls which messages are shown and recorded.  
You can use any of the following values (case-insensitive):

- `"CRITICAL"`: Show only critical errors.
- `"ERROR"`: Show errors and critical messages.
- `"WARNING"`: Show warnings, errors, and critical messages.
- `"INFO"`: Show informational messages, warnings, errors, and critical messages.
- `"DEBUG"`: Show all debug, info, warning, error, and critical messages.
- `"NOTSET"`: Show all messages (not recommended for most use cases).

**Example:**
```json
"logging": {
  "log_to_file": true,
  "log_to_console": false,
  "log_file_name": "detection.log",
  "log_level": "INFO"
}
```

**Usage Notes:**
- `"INFO"` is recommended for general use.
- `"DEBUG"` is useful for troubleshooting and development.
- `"ERROR"` and `"CRITICAL"` are best for production environments where you only want to see problems.

**How it works:**  
The value you set for `"log_level"` determines which log messages are visible in the console and/or written to the log file, depending on